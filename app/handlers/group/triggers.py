"""Тригерні слова в групі.

Тригери:
  "графік"              → скріншот Excel-файлу (діапазон комірок з налаштувань)
  "графік <прізвище>" → текстовий графік конкретної людини з БД
  "розклад"             → аліас для "графік"
  "зміна"               → аліас для "графік"
  "адмін" / "адміне" / ін. → пересилає повідомлення адмінам у приват
"""

import re
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.types import Message, FSInputFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories.setting import SettingRepository
from app.services.schedule import ScheduleService
from app.utils.schedule_formatter import format_schedule
from app.utils.text import esc
from app.utils.xlsx_screenshot import make_schedule_screenshot

router = Router(name="group:triggers")

# Тригерні слова
_SCHEDULE_WORDS = re.compile(
    r"\b(графік|график|розклад|зміна|змина)\b",
    re.IGNORECASE | re.UNICODE,
)
_ADMIN_WORDS = re.compile(
    r"\b(адмін|админ|потрібна допомога|допоможіть|допоможіть)\b",
    re.IGNORECASE | re.UNICODE,
)


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text,
)
async def handle_group_text(
    message: Message,
    bot: Bot,
    session: AsyncSession,
) -> None:
    text = message.text or ""
    lower = text.lower().strip()

    # ─── Тригер "адмін" ────────────────────────────────────
    if _ADMIN_WORDS.search(lower):
        await _handle_admin_trigger(message, bot)
        return

    # ─── Тригер "графік" ───────────────────────────────────
    if _SCHEDULE_WORDS.search(lower):
        await _handle_schedule_trigger(message, session, lower)
        return


async def _handle_schedule_trigger(
    message: Message,
    session: AsyncSession,
    lower_text: str,
) -> None:
    """
    Якщо текст містить тільки тригерне слово — скріншот всього графіка (Excel).
    Якщо після тригерного слова є прізвище — текстовий графік конкретної людини.
    """
    # видаляємо тригерне слово, беремо решту
    surname_part = _SCHEDULE_WORDS.sub("", lower_text).strip()

    if not surname_part:
        # Тільки слово "графік" — надсилаємо скріншот Excel
        await _send_excel_screenshot(message)
    else:
        # є прізвище — шукаємо в БД
        await _send_personal_schedule(message, session, surname_part)


async def _send_excel_screenshot(message: Message) -> None:
    """Надсилає скріншот Excel-файлу reply в групу."""
    try:
        repo = None  # session немає тут — читаємо налаштування з БД в service
        img_path = await make_schedule_screenshot()
        if not img_path or not Path(img_path).exists():
            await message.reply("⚠️ Графік наразі недоступний\. Зверніться до адміна\.",
                               parse_mode="MarkdownV2")
            return
        await message.reply_photo(
            photo=FSInputFile(img_path),
            caption="📅 Актуальний графік",
        )
    except Exception as e:
        logger.error(f"[trigger:schedule] screenshot error: {e}")
        await message.reply("⚠️ Не вдалося сформувати графік\. Спробуйте пізніше\.",
                           parse_mode="MarkdownV2")


async def _send_personal_schedule(
    message: Message,
    session: AsyncSession,
    surname: str,
) -> None:
    """Текстовий графік конкретної людини reply в групу."""
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
    """Пересилає повідомлення адмінам у приват з caption-тегом."""
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
