"""Налаштування Excel для скріншоту через адмін-панель.

Флоу:
1. Адмін завантажує .xlsx файл → зберігається на диск
2. Адмін задає діапазон комірок, напр. "A1:Z50"
3. Налаштування зберігається в БД і завантажується в пам'ять xlsx_screenshot
"""

from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, Document
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_back_to_admin
from app.repositories.setting import SettingRepository
from app.utils.text import esc
from app.utils.xlsx_screenshot import set_xlsx_config

router = Router(name="admin:xlsx_settings")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

_XLSX_UPLOAD_DIR = Path("data/xlsx")
_XLSX_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
)


class XlsxSettingsStates(StatesGroup):
    waiting_xlsx_file = State()
    waiting_cell_range = State()
    waiting_sheet_name = State()


@router.callback_query(F.data == "admin:xlsx_settings")
async def cb_xlsx_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    repo = SettingRepository(session)
    cfg = await repo.get_xlsx_config()
    path = cfg.get("xlsx_path") or "не задано"
    sheet = cfg.get("xlsx_sheet") or "перший аркуш"
    cell_range = cfg.get("xlsx_cell_range") or "весь аркуш"
    from app.keyboards.admin import kb_xlsx_settings
    await callback.message.edit_text(
        f"📂 *Налаштування графіка \(Excel\)*\n\n"
        f"📄 Файл: `{esc(path)}`\n"
        f"📄 Аркуш: `{esc(sheet)}`\n"
        f"📌 Діапазон: `{esc(cell_range)}`",
        reply_markup=kb_xlsx_settings(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "xlsx:upload")
async def cb_xlsx_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(XlsxSettingsStates.waiting_xlsx_file)
    await callback.message.answer(
        "📂 Надішліть *\.xlsx* файл графіка для скріншоту\.",
        parse_mode="MarkdownV2",
    )


@router.message(StateFilter(XlsxSettingsStates.waiting_xlsx_file), F.document)
async def receive_xlsx_file(
    message: Message, bot: Bot, state: FSMContext, session: AsyncSession
) -> None:
    doc: Document = message.document
    if doc.mime_type not in _ALLOWED_MIME and not (doc.file_name or "").lower().endswith(".xlsx"):
        await message.answer("❌ Потрібний файл формату *\.xlsx*\.", parse_mode="MarkdownV2")
        return

    status = await message.answer("⏳ Зберігаю файл\.\.\.", parse_mode="MarkdownV2")
    try:
        file = await bot.get_file(doc.file_id)
        save_path = _XLSX_UPLOAD_DIR / (doc.file_name or "schedule.xlsx")
        await bot.download(file, destination=str(save_path))

        repo = SettingRepository(session)
        await repo.set_xlsx_path(str(save_path))

        # Оновлюємо глобальний конфіг для screenshot-сервісу
        cfg = await repo.get_xlsx_config()
        set_xlsx_config(
            xlsx_path=str(save_path),
            sheet=cfg.get("xlsx_sheet"),
            cell_range=cfg.get("xlsx_cell_range"),
        )
        await state.clear()
        await status.edit_text(
            f"✅ Файл `{esc(doc.file_name or 'schedule.xlsx')}` збережено\!",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        logger.info(f"[xlsx_settings] new file: {save_path}")
    except Exception as e:
        logger.error(f"[xlsx_settings] upload error: {e}")
        await state.clear()
        await status.edit_text(
            f"❌ Помилка: `{esc(str(e))}`",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )


@router.callback_query(F.data == "xlsx:set_range")
async def cb_xlsx_set_range(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(XlsxSettingsStates.waiting_cell_range)
    await callback.message.answer(
        r"📌 Введіть діапазон комірок, напр. *A1:Z50*\."
        r" Цей діапазон буде зроблено картинкою при запиті ""графік""\.",
        parse_mode="MarkdownV2",
    )


@router.message(StateFilter(XlsxSettingsStates.waiting_cell_range), F.text)
async def receive_cell_range(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    import re
    cell_range = (message.text or "").strip().upper()
    if not re.match(r"^[A-Z]+\d+:[A-Z]+\d+$", cell_range):
        await message.answer(
            "❌ Неправильний формат\. Приклад: *A1:Z50*\.",
            parse_mode="MarkdownV2",
        )
        return
    await state.clear()
    repo = SettingRepository(session)
    await repo.set_xlsx_range(cell_range)
    cfg = await repo.get_xlsx_config()
    set_xlsx_config(
        xlsx_path=cfg.get("xlsx_path"),
        sheet=cfg.get("xlsx_sheet"),
        cell_range=cell_range,
    )
    await message.answer(
        f"✅ Діапазон встановлено: *{esc(cell_range)}*",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "xlsx:set_sheet")
async def cb_xlsx_set_sheet(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(XlsxSettingsStates.waiting_sheet_name)
    await callback.message.answer(
        "📄 Введіть назву аркуша Excel або натисніть ентер для використання першого:",
    )


@router.message(StateFilter(XlsxSettingsStates.waiting_sheet_name), F.text)
async def receive_sheet_name(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    sheet = (message.text or "").strip()
    await state.clear()
    repo = SettingRepository(session)
    await repo.set_xlsx_sheet(sheet)
    cfg = await repo.get_xlsx_config()
    set_xlsx_config(
        xlsx_path=cfg.get("xlsx_path"),
        sheet=sheet,
        cell_range=cfg.get("xlsx_cell_range"),
    )
    await message.answer(
        f"✅ Аркуш встановлено: *{esc(sheet)}*",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )
