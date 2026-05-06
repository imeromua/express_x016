from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.handlers.admin import (
    broadcast, reply_user, forbidden_words,
    import_schedule, xlsx_settings, schedule_search,
)
from app.keyboards.admin import kb_admin_main_menu, kb_admin_panel_inline, kb_back_to_admin
from app.repositories.user import UserRepository
from app.states.admin import AdminStates
from app.states.schedule import ScheduleStates
from app.utils.text import esc

router = Router(name="admin")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(CommandStart())
async def admin_start(message: Message) -> None:
    await message.answer(
        "🔧 *Панель адміністратора*\n"
        "Натисніть кнопку для дії ⬇️",
        reply_markup=kb_admin_main_menu(),
        parse_mode="MarkdownV2",
    )


@router.message(F.text == "🚫 Стоп-слова")
async def btn_forbidden_admin(message: Message, session: AsyncSession) -> None:
    from app.handlers.admin.forbidden_words import show_forbidden_list
    await show_forbidden_list(message, session)


@router.message(F.text == "📊 Статистика")
async def btn_stats(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    total = await repo.count_active()
    await message.answer(
        f"📊 *Статистика*\n\n"
        f"👥 Активних учасників: *{total}*",
        parse_mode="MarkdownV2",
    )


@router.message(F.text == "📅 Графік працівника", StateFilter(default_state))
async def btn_worker_schedule(message: Message, state: FSMContext) -> None:
    await state.set_state(ScheduleStates.waiting_surname)
    await message.answer("🔍 Введіть прізвище працівника:")


@router.message(F.text == "⚙️ Налаштування Excel", StateFilter(default_state))
async def btn_xlsx_settings(message: Message, session: AsyncSession) -> None:
    from app.repositories.setting import SettingRepository
    srep = SettingRepository(session)
    cfg = await srep.get_xlsx_config()
    path = cfg.get("xlsx_path") or "не задано"
    sheet = cfg.get("xlsx_sheet") or "перший аркуш"
    cell_range = cfg.get("xlsx_cell_range") or "весь аркуш"
    from app.keyboards.admin import kb_xlsx_settings
    await message.answer(
        f"⚙️ *Налаштування графіка \(Excel\)*\n\n"
        f"📄 Файл: `{esc(path)}`\n"
        f"📄 Аркуш: `{esc(sheet)}`\n"
        f"📌 Діапазон: `{esc(cell_range)}`",
        reply_markup=kb_xlsx_settings(),
        parse_mode="MarkdownV2",
    )


# --- Inline callbacks ---

@router.callback_query(F.data == "admin:back")
async def cb_admin_back(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "🔧 *Панель адміністратора*\nОберіть дію:",
        reply_markup=kb_admin_panel_inline(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    repo = UserRepository(session)
    total = await repo.count_active()
    await callback.message.edit_text(
        f"📊 *Статистика*\n\nАктивних учасників: *{total}*",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminStates.waiting_broadcast_text)
    await callback.message.edit_text(
        "📢 Надішліть повідомлення або медіа для розсилки\.",
        reply_markup=None,
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:import")
async def cb_admin_import(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "🗂 Надішліть *\.xlsx* файл графіка\.",
        reply_markup=None,
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:forbidden")
async def cb_admin_forbidden(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    from app.handlers.admin.forbidden_words import show_forbidden_list
    await show_forbidden_list(callback.message, session)


@router.callback_query(F.data == "admin:xlsx_settings")
async def cb_admin_xlsx_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    from app.handlers.admin.xlsx_settings import cb_xlsx_settings
    await cb_xlsx_settings(callback, session)


router.include_router(broadcast.router)
router.include_router(reply_user.router)
router.include_router(forbidden_words.router)
router.include_router(import_schedule.router)
router.include_router(xlsx_settings.router)
router.include_router(schedule_search.router)
