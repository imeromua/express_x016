"""Налаштування Excel для скріншоту через адмін-панель."""

from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, Document
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_back_to_admin, kb_xlsx_settings
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


async def _show_xlsx_menu(target, session: AsyncSession) -> None:
    """Показати меню налаштувань Excel.
    target — CallbackQuery (робимо edit_text) або Message (робимо answer).
    """
    repo = SettingRepository(session)
    cfg = await repo.get_xlsx_config()
    path = cfg.get("xlsx_path") or "не задано"
    sheet = cfg.get("xlsx_sheet") or "перший аркуш"
    cell_range = cfg.get("xlsx_cell_range") or "весь аркуш"

    text = (
        f"⚙️ *Налаштування графіка \\(Excel\\)*\n\n"
        f"📄 Файл: `{esc(path)}`\n"
        f"📄 Аркуш: `{esc(sheet)}`\n"
        f"📌 Діапазон: `{esc(cell_range)}`"
    )
    kb = kb_xlsx_settings()

    if isinstance(target, CallbackQuery):
        await target.answer()
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="MarkdownV2")
        except Exception:
            # Якщо edit не вдалось (напр. те саме повідомлення) — надсилаємо нове
            await target.message.answer(text, reply_markup=kb, parse_mode="MarkdownV2")
    else:
        # Message (виклик через Reply-кнопку)
        await target.answer(text, reply_markup=kb, parse_mode="MarkdownV2")


# ─── Reply-кнопка «⚙️ Налаштування Excel» ───────────────────────────

@router.message(F.text == "⚙️ Налаштування Excel")
async def btn_xlsx_settings_reply(message: Message, session: AsyncSession) -> None:
    await _show_xlsx_menu(message, session)


# ─── Inline callbacks ───────────────────────────────────────────────

@router.callback_query(F.data == "admin:xlsx_settings")
async def cb_xlsx_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    await _show_xlsx_menu(callback, session)


@router.callback_query(F.data == "xlsx:upload")
async def cb_xlsx_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(XlsxSettingsStates.waiting_xlsx_file)
    await callback.message.answer(
        r"📂 Надішліть *\.xlsx* файл графіка для скріншоту\.",
        parse_mode="MarkdownV2",
    )


@router.message(StateFilter(XlsxSettingsStates.waiting_xlsx_file), F.document)
async def receive_xlsx_file(
    message: Message, bot: Bot, state: FSMContext, session: AsyncSession
) -> None:
    doc: Document = message.document
    if doc.mime_type not in _ALLOWED_MIME and not (doc.file_name or "").lower().endswith(".xlsx"):
        await message.answer(r"❌ Потрібний файл формату *\.xlsx*\.", parse_mode="MarkdownV2")
        return

    status = await message.answer(r"⏳ Зберігаю файл\.\.\.", parse_mode="MarkdownV2")
    try:
        file = await bot.get_file(doc.file_id)
        save_path = _XLSX_UPLOAD_DIR / (doc.file_name or "schedule.xlsx")
        await bot.download(file, destination=str(save_path))

        repo = SettingRepository(session)
        await repo.set_xlsx_path(str(save_path))
        cfg = await repo.get_xlsx_config()
        set_xlsx_config(
            xlsx_path=str(save_path),
            sheet=cfg.get("xlsx_sheet"),
            cell_range=cfg.get("xlsx_cell_range"),
        )
        await state.clear()
        await status.edit_text(
            f"✅ Файл `{esc(doc.file_name or 'schedule.xlsx')}` збережено\\!",
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
        r"📌 Введіть діапазон комірок, напр\. *B4:AK14*\. Цей прямокутник буде зроблено картинкою при запиті *графік*\.",
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
            r"❌ Неправильний формат\. Приклад: *B4:AK14*\.",
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
    logger.info(f"[xlsx_settings] cell_range={cell_range}")


@router.callback_query(F.data == "xlsx:set_sheet")
async def cb_xlsx_set_sheet(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(XlsxSettingsStates.waiting_sheet_name)
    await callback.message.answer(
        r"📄 Введіть назву аркуша Excel \(або залиште порожнім для першого аркуша\):",
        parse_mode="MarkdownV2",
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
        sheet=sheet or None,
        cell_range=cfg.get("xlsx_cell_range"),
    )
    label = sheet or "перший аркуш"
    await message.answer(
        f"✅ Аркуш встановлено: *{esc(label)}*",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )
    logger.info(f"[xlsx_settings] sheet={sheet!r}")
