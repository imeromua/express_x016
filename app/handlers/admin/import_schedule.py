"""Імпорт графіку з .xlsx.
Адмін надсилає файл — бот парсить і виконує UPSERT.
⚠️  Парсер — STUB до отримання реального файлу (див. app/integrations/xlsx_parser.py)
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, Document
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.integrations.xlsx_parser import parse_schedule_xlsx, XlsxParseError
from app.services.schedule import ScheduleService

router = Router(name="admin:import")
router.message.filter(IsAdminFilter())

_ALLOWED_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
)


@router.message(Command("import"))
async def cmd_import_hint(message: Message) -> None:
    await message.answer(
        "📂 Надішліть *.xlsx* файл графіка для імпорту\.

"
        "⚠️ Увага: парсер працює в режимі заглушки\.
"
        "Після отримання реального файлу — уточніться структура колонок\.",
        parse_mode="MarkdownV2",
    )


@router.message(F.document)
async def handle_xlsx_upload(
    message: Message,
    bot: Bot,
    session: AsyncSession,
) -> None:
    doc: Document = message.document

    # Перевіряємо тип файлу
    if doc.mime_type not in _ALLOWED_MIME and not (
        doc.file_name or ""
    ).lower().endswith(".xlsx"):
        await message.answer(
            "❌ Потрібний файл формату *.xlsx*\.",
            parse_mode="MarkdownV2",
        )
        return

    status = await message.answer(„⏳ Обробка файлу\.\.\.\u201c, parse_mode="MarkdownV2")

    try:
        # Завантажуємо файл через file_id (не зберігаємо на диск)
        file = await bot.get_file(doc.file_id)
        file_bytes = await bot.download_file(file.file_path)
        raw = file_bytes.read()

        rows = parse_schedule_xlsx(raw)
        svc = ScheduleService(session)
        count = await svc.import_from_rows(rows)

        await status.edit_text(
            f"✅ Імпорт завершено\!\n"
            f"Оброблено записів: *{count}*",
            parse_mode="MarkdownV2",
        )
        logger.info(
            f"[import] Адмін {message.from_user.id}: "
            f"імпортовано {count} записів з {doc.file_name!r}"
        )

    except XlsxParseError as e:
        await status.edit_text(
            f"❌ Помилка парсингу: `{_esc(str(e))}`",
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.error(f"[import] Несподівана помилка: {e}")
        await status.edit_text(
            "❌ Сталася неочікувана помилка\. Адміна повідомлено\.",
            parse_mode="MarkdownV2",
        )


def _esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
