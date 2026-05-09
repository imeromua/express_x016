from aiogram import Router, F, Bot
from aiogram.types import Message, Document
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.integrations.xlsx_parser import parse_schedule_xlsx, XlsxParseError
from app.keyboards.admin import kb_back_to_admin
from app.services.schedule import ScheduleService
from app.utils.text import esc

router = Router(name="admin:import")
router.message.filter(IsAdminFilter())

_ALLOWED_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
)


@router.message(F.document)
async def handle_xlsx_upload(
    message: Message, bot: Bot, session: AsyncSession
) -> None:
    doc: Document = message.document
    if doc.mime_type not in _ALLOWED_MIME and not (doc.file_name or "").lower().endswith(".xlsx"):
        await message.answer(
            r"❌ Потрібний файл формату *\.xlsx*\.",
            parse_mode="MarkdownV2",
        )
        return

    status = await message.answer(r"⏳ Обробка файлу\.\.\.", parse_mode="MarkdownV2")
    try:
        file = await bot.get_file(doc.file_id)
        file_bytes = await bot.download_file(file.file_path)
        raw = file_bytes.read()
        rows = parse_schedule_xlsx(raw)
        svc = ScheduleService(session)
        count = await svc.import_from_rows(rows)

        # Кількість унікальних співробітників
        unique_employees = len({r["pib"] for r in rows})

        await status.edit_text(
            rf"✅ Імпорт завершено\!\.\n"
            rf"👥 Співробітників: *{unique_employees}*\n"
            rf"📅 Записів у БД: *{count}*",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        logger.info(
            f"[import] {message.from_user.id}: {count} записів, "
            f"{unique_employees} співробітників з {doc.file_name!r}"
        )
    except XlsxParseError as e:
        await status.edit_text(
            rf"❌ Помилка парсингу: `{esc(str(e))}`",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.exception(f"[import] {e}")
        await status.edit_text(
            r"❌ Неочікувана помилка при імпорті\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
