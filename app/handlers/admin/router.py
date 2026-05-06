"""Адмін-роутер: reply-кнопки + inline callbacks."""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.handlers.admin import broadcast, reply_user, forbidden_words, import_schedule
from app.keyboards.admin import kb_admin_main_menu, kb_admin_panel_inline
from app.repositories.user import UserRepository
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


# --- Reply-кнопки — відкривають inline-панель ---

@router.message(F.text == "📢 Розсилка")
async def btn_broadcast(message: Message) -> None:
    from app.handlers.admin.broadcast import start_broadcast
    await start_broadcast(message)


@router.message(F.text == "📂 Імпорт графіка")
async def btn_import(message: Message) -> None:
    await message.answer(
        "📂 Надішліть *\.xlsx* файл графіка\.",
        parse_mode="MarkdownV2",
    )


@router.message(F.text == "🚫 Стоп-слова")
async def btn_forbidden(message: Message) -> None:
    from app.handlers.admin.forbidden_words import show_forbidden_list
    await show_forbidden_list(message)


@router.message(F.text == "📊 Статистика")
async def btn_stats(message: Message, session: AsyncSession) -> None:
    repo = UserRepository(session)
    total = await repo.count_active()
    await message.answer(
        f"📊 *Статистика*\n\n"
        f"👥 Активних учасників: *{total}*",
        parse_mode="MarkdownV2",
    )


@router.message(F.text == "📅 Графік працівника")
async def btn_worker_schedule(message: Message, session: AsyncSession) -> None:
    from app.keyboards.admin import kb_back_to_admin
    await message.answer(
        "🔍 Введіть прізвище працівника:",
        reply_markup=kb_back_to_admin(),
    )
    from app.states.schedule import ScheduleStates
    # Передаємо до загального schedule-хендлера через schedule router


# --- Inline callbacks панелі ---

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
    from app.keyboards.admin import kb_back_to_admin
    await callback.message.edit_text(
        f"📊 *Статистика*\n\nАктивних учасників: *{total}*",
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(callback: CallbackQuery) -> None:
    await callback.answer()
    from app.handlers.admin.broadcast import start_broadcast
    await start_broadcast(callback.message)


@router.callback_query(F.data == "admin:import")
async def cb_admin_import(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📂 Надішліть *\.xlsx* файл графіка\.",
        reply_markup=None,
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:forbidden")
async def cb_admin_forbidden(callback: CallbackQuery) -> None:
    await callback.answer()
    from app.handlers.admin.forbidden_words import show_forbidden_list
    await show_forbidden_list(callback.message)


router.include_router(broadcast.router)
router.include_router(reply_user.router)
router.include_router(forbidden_words.router)
router.include_router(import_schedule.router)
