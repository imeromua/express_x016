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
from app.keyboards.admin import kb_admin_main_menu, kb_back_to_admin
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
        "\U0001f527 *\u041f\u0430\u043d\u0435\u043b\u044c \u0430\u0434\u043c\u0456\u043d\u0456\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430*\n"
        "\u041d\u0430\u0442\u0438\u0441\u043d\u0456\u0442\u044c \u043a\u043d\u043e\u043f\u043a\u0443 \u0434\u043b\u044f \u0434\u0456\u0457 \u2b07\ufe0f",
        reply_markup=kb_admin_main_menu(),
        parse_mode="MarkdownV2",
    )


# ─── Reply-кнопки ──────────────────────────────────────────────────

@router.message(F.text == "📢 Розсилка")
async def btn_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_broadcast_text)
    await message.answer(
        r"📢 Надішліть повідомлення або медіа для розсилки\.",
        parse_mode="MarkdownV2",
    )


@router.message(F.text == "📂 Імпорт графіка", StateFilter(default_state))
async def btn_import_schedule(message: Message, state: FSMContext) -> None:
    """Reply-кнопка — переводимо в стан очікування файлу."""
    await state.set_state(AdminStates.waiting_xlsx_import)
    await message.answer(
        r"🗂 Надішліть *\.xlsx* файл графіка\.",
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
    from app.keyboards.admin import kb_xlsx_settings
    srep = SettingRepository(session)
    cfg = await srep.get_xlsx_config()
    path = cfg.get("xlsx_path") or "не задано"
    sheet = cfg.get("xlsx_sheet") or "перший аркуш"
    cell_range = cfg.get("xlsx_cell_range") or "весь аркуш"
    await message.answer(
        f"⚙️ *Налаштування графіка \\(Excel\\)*\n\n"
        f"📄 Файл: `{esc(path)}`\n"
        f"📄 Аркуш: `{esc(sheet)}`\n"
        f"📌 Діапазон: `{esc(cell_range)}`",
        reply_markup=kb_xlsx_settings(),
        parse_mode="MarkdownV2",
    )


# ─── Inline callbacks ─────────────────────────────────────────────────

@router.callback_query(F.data == "admin:back")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🔧 *Панель адміністратора*\n"
        "Натисніть кнопку для дії ⬇️",
        reply_markup=kb_admin_main_menu(),
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
        r"📢 Надішліть повідомлення або медіа для розсилки\.",
        reply_markup=None,
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:import")
async def cb_admin_import(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminStates.waiting_xlsx_import)
    await callback.message.edit_text(
        r"🗂 Надішліть *\.xlsx* файл графіка\.",
        reply_markup=None,
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:forbidden")
async def cb_admin_forbidden(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    from app.handlers.admin.forbidden_words import show_forbidden_list
    await show_forbidden_list(callback.message, session)


router.include_router(broadcast.router)
router.include_router(reply_user.router)
router.include_router(forbidden_words.router)
router.include_router(import_schedule.router)
router.include_router(xlsx_settings.router)
router.include_router(schedule_search.router)
