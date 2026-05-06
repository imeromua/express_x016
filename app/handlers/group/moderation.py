from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ChatType
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.integrations.virustotal import check_url, VTVerdict
from app.repositories.setting import SettingRepository
from app.utils.url_extractor import extract_urls, is_whitelisted

router = Router(name="group:moderation")


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.entities | F.caption_entities,
)
async def handle_links(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    redis: Redis,
) -> None:
    """
    Перевіряє URL в групових повідомленнях через VirusTotal.

    Пайплайн: extract → normalize → whitelist → cache → VT → action
    """
    settings = get_settings()
    urls = extract_urls(message)
    if not urls:
        return

    setting_repo = SettingRepository(session)
    whitelist = await setting_repo.get_url_whitelist()

    suspicious_urls = []

    for url in urls:
        # 1. Whitelist
        if is_whitelisted(url, whitelist):
            logger.debug(f"[moderation] whitelist: {url[:60]}")
            continue

        # 2. VirusTotal
        verdict = await check_url(
            url=url,
            api_key=settings.virustotal_api_key,
            redis=redis,
        )

        if verdict in (VTVerdict.MALICIOUS, VTVerdict.SUSPICIOUS):
            suspicious_urls.append((url, verdict))

    if not suspicious_urls:
        return

    # Видаляємо повідомлення
    try:
        await message.delete()
        logger.warning(
            f"[moderation] Видалено повідомлення від {message.from_user.id} "
            f"з підозрілими URL: {[u for u, _ in suspicious_urls]}"
        )
    except Exception as e:
        logger.error(f"[moderation] Не вдалося видалити: {e}")

    # Повідомляємо адмінів
    user = message.from_user
    url_list = "\n".join(
        f"• `{_esc(u[:80])}` — *{v.value}*"
        for u, v in suspicious_urls
    )
    alert = (
        f"⚠️ *Підозріле посилання*\n"
        f"Користувач: [{_esc(user.full_name)}](tg://user?id={user.id})\n"
        f"Чат: `{message.chat.id}`\n\n"
        f"{url_list}"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, alert, parse_mode="MarkdownV2")
        except Exception:
            pass

    # Попередження юзеру в приватні
    try:
        await bot.send_message(
            user.id,
            "⚠️ Твоє повідомлення було видалено: містило потенційно небезпечне посилання\.
"
            "Будь ласка, дотримуйся правил спільноти\.",
            parse_mode="MarkdownV2",
        )
    except Exception:
        pass


def _esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
