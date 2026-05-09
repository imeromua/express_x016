"""Тригерні слова в групі.

Тригери:
  "графік"              → скріншот Excel-файлу (reply в групі)
  "графік <прізвище>" → текстовий графік конкретної людини
  "адмін" / "допоможіть"  → пересилає адмінам у приват

Throttling: один запит графіка на 30 секунд на чат (не на юзера).
"""

import re
from datetime import date
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.types import Message, FSInputFile, ChatMemberUpdated
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories.schedule import ScheduleRepository
from app.repositories.user import UserRepository
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

_THROTTLE_TTL = 30
_THROTTLE_KEY = "trigger:schedule:{chat_id}"


# ─── Авто-реєстрація при вході нового учасника ──────────────────────────

@router.chat_member(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def handle_new_member(
    event: ChatMemberUpdated,
    session: AsyncSession,
) -> None:
    """Upsert користувача при вході до групи."""
    settings = get_settings()
    if event.chat.id != settings.group_id:
        return

    # Зареєструємо лише нових (не вихід із групи)
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    user = event.new_chat_member.user

    if user.is_bot:
        return

    # member/restricted -> вхід до групи
    if new_status in ("member", "restricted") and old_status in ("left", "kicked", "banned"):
        try:
            repo = UserRepository(session)
            await repo.upsert(
                user_id=user.id,
                username=user.username,
            )
            logger.info(f"[GroupTracker] Новий учасник: {user.id} @{user.username}")
        except Exception as e:
            logger.warning(f"[GroupTracker] upsert new member error: {e}")


# ─── Текстові повідомлення ────────────────────────────────────────────

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
    text = (message.text or "").strip()
    lower = text.lower()

    if _ADMIN_RE.search(lower):
        await _handle_admin_trigger(message, bot)
        return

    if _SCHEDULE_RE.search(lower):
        surname_part = _SCHEDULE_RE.sub("", text).strip()
        if not surname_part:
            await _send_excel_screenshot(message, redis)
        else:
            await _send_personal_schedule(message, session, surname_part)


async def _send_excel_screenshot(message: Message, redis: Redis) -> None:
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
                r"⚠️ Графік наразі недоступний\. Зверніться до адміна\.",
                parse_mode="MarkdownV2",
            )
            return

        await message.reply_photo(
            photo=FSInputFile(img_path),
            caption="📅 Актуальний графік",
        )
        await redis.setex(throttle_key, _THROTTLE_TTL, "1")

    except Exception as e:
        logger.error(f"[trigger:schedule] screenshot error: {e}")
        await message.reply(
            r"⚠️ Не вдалося сформувати графік\. Спробуйте пізніше\.",
            parse_mode="MarkdownV2",
        )


async def _send_personal_schedule(
    message: Message,
    session: AsyncSession,
    surname: str,
) -> None:
    repo = ScheduleRepository(session)
    pib = await repo.find_pib_exact(surname)
    if not pib:
        await message.reply(
            f"❌ Працівника *{esc(surname)}* не знайдено\."
            r" Перевірте правопис прізвища\.",
            parse_mode="MarkdownV2",
        )
        return

    records = await repo.get_upcoming(pib, date.today())
    text = format_schedule(records, pib)
    await message.reply(text, parse_mode="MarkdownV2")


async def _handle_admin_trigger(message: Message, bot: Bot) -> None:
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
            r"✅ Адміністратор отримав ваше повідомлення\. Очікуйте відповіді\.",
            parse_mode="MarkdownV2",
        )
    else:
        await message.reply(
            r"⚠️ Не вдалося надіслати запит адміну\. Спробуйте пізніше\.",
            parse_mode="MarkdownV2",
        )
