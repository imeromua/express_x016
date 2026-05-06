"""Адмін-роутер: reply-кнопки + inline callbacks."""

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.handlers.admin import broadcast, reply_user, forbidden_words, import_schedule
from app.keyboards.admin import kb_admin_main_menu, kb_admin_panel_inline, kb_back_to_admin
from app.repositories.user import UserRepository
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


# ─── Reply-кнопки ───────────────────────────────────────────────

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
    """Запускає пошук графіку за прізвищем — через FSMState."""
    await state.set_state(ScheduleStates.waiting_surname)
    await message.answer(
        "🔍 Введіть прізвище працівника:",
    )


# ─── Inline callbacks панелі ─────────────────────────────────────

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
    """Inline-кнопка розсилки — коректно передає state."""
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
async def cb_admin_forbidden(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Inline-кнопка стоп-слів — передає session."""
    await callback.answer()
    from app.handlers.admin.forbidden_words import show_forbidden_list
    await show_forbidden_list(callback.message, session)


router.include_router(broadcast.router)
router.include_router(reply_user.router)
router.include_router(forbidden_words.router)
router.include_router(import_schedule.router)

# Імпортуємо AdminStates тут щоб не дублювати
from app.states.admin import AdminStates  # noqa: E402
