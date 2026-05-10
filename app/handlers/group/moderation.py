"""Moderation handler: URL, файли, фото, підозрілий текст.

Пайплайн:
  Текст  → detect_threats (SQL/XSS/Shell) → інфо адміну
  URL    → whitelist → VT check_url → видалення + попередження
  Фото   → завантажуємо найбільшої розділ. → VT check_file
  Файл  → завантажуємо файл → VT check_file
"""

from __future__ import annotations

import io

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.types import Message
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.integrations.virustotal import check_url, check_file, VTVerdict
from app.repositories.setting import SettingRepository
from app.utils.url_extractor import extract_urls, is_whitelisted
from app.utils.threat_detector import detect_threats

router = Router(name="group:moderation")

_GROUP_FILTER = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})

# Максимальний розмір файлу для VT перевірки (32 МБ — free tier limit)
_MAX_FILE_SIZE = 32 * 1024 * 1024


def _esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


async def _alert_admins(bot: Bot, message: Message, lines: list[str]) -> None:
    user = message.from_user
    body = "\n".join(lines)
    text = (
        f"⚠️ *Подія в групі*\n"
        f"Користувач: [{_esc(user.full_name)}](tg://user?id={user.id})\n"
        f"Чат: `{message.chat.id}`\n\n"
        f"{body}"
    )
    settings = get_settings()
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="MarkdownV2")
        except Exception:
            pass


async def _warn_user(bot: Bot, user_id: int, reason: str) -> None:
    try:
        await bot.send_message(
            user_id,
            f"⚠️ Твоє повідомлення видалено: {_esc(reason)}\."
            "Будь ласка, дотримуйся правил спільноти\.",
            parse_mode="MarkdownV2",
        )
    except Exception:
        pass


async def _try_delete(message: Message) -> bool:
    try:
        await message.delete()
        return True
    except Exception as e:
        logger.error(f"[moderation] Не вдалось видалити: {e}")
        return False


# ─── Текст + URL ──────────────────────────────────────────────

@router.message(
    _GROUP_FILTER,
    F.text | F.caption,
)
async def handle_text(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    redis: Redis,
) -> None:
    settings = get_settings()
    text = message.text or message.caption or ""

    # 1. Перевірка тексту на патерни атак
    threats = detect_threats(text)
    if threats:
        lines = []
        for t in threats:
            lines.append(f"▪️ *{_esc(t.category)}*: `{_esc(t.snippet)}`")
        logger.warning(
            f"[moderation] Threat в повідомленні uid={message.from_user.id}: "
            f"{[t.category for t in threats]}"
        )
        await _alert_admins(bot, message, ["🛡 *Підозрілий текст*"] + lines)
        # Не видаляємо автоматично — адмін вирішує самостійно

    # 2. URL-перевірка (тільки якщо є entities)
    if not (message.entities or message.caption_entities):
        return

    urls = extract_urls(message)
    if not urls:
        return

    setting_repo = SettingRepository(session)
    whitelist = await setting_repo.get_url_whitelist()
    suspicious_urls = []

    for url in urls:
        if is_whitelisted(url, whitelist):
            logger.debug(f"[moderation] whitelist: {url[:60]}")
            continue

        verdict = await check_url(
            url=url,
            api_key=settings.virustotal_api_key,
            redis=redis,
        )
        if verdict in (VTVerdict.MALICIOUS, VTVerdict.SUSPICIOUS):
            suspicious_urls.append((url, verdict))

    if not suspicious_urls:
        return

    await _try_delete(message)
    logger.warning(
        f"[moderation] Видалено: uid={message.from_user.id} "
        f"{[u for u, _ in suspicious_urls]}"
    )

    url_lines = [
        f"• `{_esc(u[:80])}` — *{_esc(v.value)}*"
        for u, v in suspicious_urls
    ]
    await _alert_admins(bot, message, ["🔗 *Підозріле посилання*"] + url_lines)
    await _warn_user(bot, message.from_user.id, "містило потенційно небезпечне посилання")


# ─── Фото ─────────────────────────────────────────────────────────

@router.message(
    _GROUP_FILTER,
    F.photo,
)
async def handle_photo(
    message: Message,
    bot: Bot,
    redis: Redis,
) -> None:
    settings = get_settings()
    if not settings.virustotal_api_key:
        return

    # Беремо найбільше розділення
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > _MAX_FILE_SIZE:
        logger.debug(f"[moderation] Фото завелика ({photo.file_size} б): пропуск")
        return

    try:
        file = await bot.get_file(photo.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, destination=buf)
        file_bytes = buf.getvalue()
    except Exception as e:
        logger.warning(f"[moderation] Не вдалось завантажити фото: {e}")
        return

    verdict = await check_file(
        file_bytes=file_bytes,
        api_key=settings.virustotal_api_key,
        redis=redis,
        filename=f"photo_{photo.file_unique_id}.jpg",
    )

    logger.info(f"[moderation] Фото uid={message.from_user.id} → {verdict.value}")

    if verdict in (VTVerdict.MALICIOUS, VTVerdict.SUSPICIOUS):
        await _try_delete(message)
        await _alert_admins(
            bot, message,
            [
                f"🖼 *Підозріле фото* — VT: *{_esc(verdict.value)}*",
                f"Розмір: {photo.width}×{photo.height}, {photo.file_size} б",
            ]
        )
        await _warn_user(bot, message.from_user.id, "фото визнано потенційно небезпечним")


# ─── Файли / документи ────────────────────────────────────────────

@router.message(
    _GROUP_FILTER,
    F.document,
)
async def handle_document(
    message: Message,
    bot: Bot,
    redis: Redis,
) -> None:
    settings = get_settings()
    if not settings.virustotal_api_key:
        return

    doc = message.document
    if doc.file_size and doc.file_size > _MAX_FILE_SIZE:
        logger.debug(f"[moderation] Документ завеликий ({doc.file_size} б): пропуск")
        return

    try:
        file = await bot.get_file(doc.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, destination=buf)
        file_bytes = buf.getvalue()
    except Exception as e:
        logger.warning(f"[moderation] Не вдалось завантажити документ: {e}")
        return

    verdict = await check_file(
        file_bytes=file_bytes,
        api_key=settings.virustotal_api_key,
        redis=redis,
        filename=doc.file_name or f"doc_{doc.file_unique_id}",
    )

    logger.info(
        f"[moderation] Документ '{doc.file_name}' "
        f"uid={message.from_user.id} → {verdict.value}"
    )

    if verdict in (VTVerdict.MALICIOUS, VTVerdict.SUSPICIOUS):
        await _try_delete(message)
        await _alert_admins(
            bot, message,
            [
                f"📄 *Підозрілий файл* — VT: *{_esc(verdict.value)}*",
                f"Файл: `{_esc(doc.file_name or '?')}`, {doc.file_size} б",
                f"MIME: `{_esc(doc.mime_type or '?')}`",
            ]
        )
        await _warn_user(bot, message.from_user.id, f"файл `{doc.file_name}` визнано потенційно небезпечним")
