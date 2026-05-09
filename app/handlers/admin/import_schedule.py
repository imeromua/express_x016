from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Document
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.integrations.xlsx_parser import parse_schedule_xlsx, XlsxParseError
from app.keyboards.admin import kb_back_to_admin
from app.services.schedule import ScheduleService
from app.states.admin import AdminStates
from app.utils.text import esc

router = Router(name="admin:import")
router.message.filter(IsAdminFilter())

_ALLOWED_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
)


@router.message(
    StateFilter(AdminStates.waiting_xlsx_import),
    F.document,
)
async def handle_xlsx_upload(
    message: Message, bot: Bot, state: FSMContext, session: AsyncSession
) -> None:
    """Приймає .xlsx файл тільки якщо адмін в стані waiting_xlsx_import."""
    await state.clear()
    doc: Document = message.document

    if doc.mime_type not in _ALLOWED_MIME and not (doc.file_name or "").lower().endswith(".xlsx"):
        await message.answer(
            r"\u274c Потрібний файл формату *\.xlsx*\.",
            parse_mode="MarkdownV2",
        )
        return

    logger.info(f"[import] Початок імпорту: {doc.file_name!r} від {message.from_user.id}")
    status = await message.answer(r"⏳ Обробка файлу\.\.\.", parse_mode="MarkdownV2")
    try:
        file = await bot.get_file(doc.file_id)
        file_bytes = await bot.download_file(file.file_path)
        raw = file_bytes.read()
        rows = parse_schedule_xlsx(raw)
        logger.info(f"[import] Парсинг завершено: {len(rows)} рядків")
        svc = ScheduleService(session)
        count = await svc.import_from_rows(rows)
        unique_employees = len({r["pib"] for r in rows})

        text = (
            f"\u2705 Імпорт завершено\\!\n"
            f"\U0001f465 Співробітників: *{unique_employees}*\n"
            f"\U0001f4c5 Записів у БД: *{count}*"
        )
        await status.edit_text(
            text,
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        logger.info(
            f"[import] Готово: {count} записів, "
            f"{unique_employees} співробітників з {doc.file_name!r}"
        )
    except XlsxParseError as e:
        logger.warning(f"[import] XlsxParseError: {e}")
        await status.edit_text(
            f"❌ Помилка парсингу: `{esc(str(e))}`",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.exception(f"[import] Неочікувана помилка: {e}")
        await status.edit_text(
            r"❌ Неочікувана помилка при імпорті\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
