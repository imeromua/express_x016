"""Тригерні слова в групі.

Тригери:
  "графік"              → скріншот Excel-файлу (reply в групі)
  "графік <прізвище>" → текстовий графік конкретної людини
  "розклад" / "зміна"     → аліаси "графік"
  "адмін" / "допоможіть"  → пересилає адмінам у приват

Throttling: один запит графіка на 30 секунд на чат (не на юзера).
"""

import re
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.types import Message, FSInputFile
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.schedule import ScheduleService
from app.utils.schedule_formatter import format_schedule
from app.utils.text import esc
from app.utils.xlsx_screenshot import make_schedule_screenshot

router = Router(name="group:triggers")

_SCHEDULE_RE = re.compile(
    r"\b(графік|график|розклад|зміна|змина)\b",
    re.IGNORECASE | re.UNICODE,
)
_ADMIN_RE = re.compile(
    r"\b(адмін|админ|допоможіть|потрібна допомога)\b",
    re.IGNORECASE | re.UNICODE,
)

# Redis-ключ throttle: 1 скріншот на chat за 30 секунд
_THROTTLE_TTL = 30
_THROTTLE_KEY = "trigger:schedule:{chat_id}"


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text,
)
async def handle_group_text(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    redis: Redis,
) -> None:
    text = message.text or ""
    lower = text.lower().strip()

    # ─── тригер "адмін" ───────────────────────────────────────
    if _ADMIN_RE.search(lower):
        await _handle_admin_trigger(message, bot)
        return

    # ─── тригер "графік" ──────────────────────────────────────
    if _SCHEDULE_RE.search(lower):
        surname_part = _SCHEDULE_RE.sub("", lower).strip()
        if not surname_part:
            await _send_excel_screenshot(message, redis)
        else:
            await _send_personal_schedule(message, session, surname_part)


async def _send_excel_screenshot(message: Message, redis: Redis) -> None:
    """Throttle: один скріншот на 30с на весь чат."""
    throttle_key = _THROTTLE_KEY.format(chat_id=message.chat.id)
    if await redis.exists(throttle_key):
        ttl = await redis.ttl(throttle_key)
        await message.reply(
            f"⏳ Графік вже був надісланий\. Повторний запит через *{ttl}* сек\.",
            parse_mode="MarkdownV2",
        )
        return

    try:
        img_path = await make_schedule_screenshot()
        if not img_path or not Path(img_path).exists():
            await message.reply(
                "⚠️ Графік наразі недоступний\. "
                "Зверніться до адміна\.",
                parse_mode="MarkdownV2",
            )
            return

        await message.reply_photo(
            photo=FSInputFile(img_path),
            caption="📅 Актуальний графік",
        )
        # встановлюємо throttle
        await redis.setex(throttle_key, _THROTTLE_TTL, "1")

    except Exception as e:
        logger.error(f"[trigger:schedule] screenshot error: {e}")
        await message.reply(
            "⚠️ Не вдалося сформувати графік\. Спробуйте пізніше\.",
            parse_mode="MarkdownV2",
        )


async def _send_personal_schedule(
    message: Message,
    session: AsyncSession,
    surname: str,
) -> None:
    """Reply з текстовим графіком конкретної людини."""
    svc = ScheduleService(session)
    pib = await svc.resolve_pib(surname)
    if not pib:
        await message.reply(
            f"❌ Працівника з прізвищем *{esc(surname)}* не знайдено\."
            " Перевірте правопис прізвища\.",
            parse_mode="MarkdownV2",
        )
        return
    records = await svc.get_upcoming_for_pib(pib)
    text = format_schedule(records, pib)
    await message.reply(text, parse_mode="MarkdownV2")


async def _handle_admin_trigger(message: Message, bot: Bot) -> None:
    """Пересилає повідомлення адмінам у приват."""
    settings = get_settings()
    user = message.from_user
    tag = f"#user:{user.id}"
    caption = (
        f"✉️ Звернення з групи від "
        f"[{esc(user.full_name)}](tg://user?id={user.id})\n"
        f"{tag}"
    )
    forwarded = False
    for admin_id in settings.admin_ids:
        try:
            await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                parse_mode="MarkdownV2",
            )
            forwarded = True
        except Exception as e:
            logger.warning(f"[trigger:admin] {admin_id}: {e}")

    if forwarded:
        await message.reply(
            "✅ Адміністратор отримав ваше повідомлення\. Очікуйте відповіді\.",
            parse_mode="MarkdownV2",
        )
    else:
        await message.reply(
            "⚠️ Не вдалося надіслати запит адміну\. Спробуйте пізніше\.",
            parse_mode="MarkdownV2",
        )
