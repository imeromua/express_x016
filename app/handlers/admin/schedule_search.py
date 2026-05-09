"""Пошук графіка працівника з адмін-панелі.

Флоу:
  1. Адмін натискає "📅 Графік працівника" (ScheduleStates.waiting_surname)
  2. Бот виводить inline-список всіх ПІБ
  3. Адмін натискає ПІБ → бот виводить графік
"""

from datetime import date

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_back_to_admin, kb_pib_picker
from app.repositories.schedule import ScheduleRepository
from app.services.schedule import ScheduleService
from app.states.schedule import ScheduleStates
from app.utils.schedule_formatter import format_schedule
from app.utils.text import esc

router = Router(name="admin:schedule_search")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

_PREFIX = "sched_pick"


async def _show_schedule_picker(
    target,  # Message | CallbackQuery
    session: AsyncSession,
    state: FSMContext,
    page: int = 0,
) -> None:
    await state.clear()
    repo = ScheduleRepository(session)
    pib_list = await repo.get_all_unique_pib()

    if not pib_list:
        text = r"⚠️ Графік порожній\. Спочатку імпортуйте Excel\."
        if isinstance(target, Message):
            await target.answer(text, parse_mode="MarkdownV2")
        else:
            await target.message.edit_text(text, parse_mode="MarkdownV2")
        return

    kb = kb_pib_picker(
        pib_list=pib_list,
        callback_prefix=_PREFIX,
        page=page,
        back_cb="admin:back",
    )
    text = "📅 Оберіть працівника для перегляду графіка:"
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb)
    else:
        await target.message.edit_text(text, reply_markup=kb)


@router.message(StateFilter(ScheduleStates.waiting_surname), F.text)
async def receive_admin_surname(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    # Ігноруємо reply-кнопки адмінки
    _ADMIN_BTNS = {
        "📢 розсилка", "📂 імпорт графіка",
        "🚫 стоп-слова", "📊 статистика",
        "📅 графік працівника", "⚙️ налаштування excel",
    }
    if (message.text or "").strip().lower() in _ADMIN_BTNS:
        await state.clear()
        return
    await _show_schedule_picker(message, session, state)


# Пагінація списку
@router.callback_query(F.data.regexp(rf"^{_PREFIX}:page:(\d+)$"))
async def cb_sched_pick_page(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    page = int(callback.data.split(":")[2])
    await _show_schedule_picker(callback, session, state, page=page)


# Вибір ПІБ
@router.callback_query(F.data.regexp(rf"^{_PREFIX}:(?!page:).+$"))
async def cb_sched_pick_select(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    pib = callback.data[len(_PREFIX) + 1:]  # все після префіксу:
    await state.clear()

    repo = ScheduleRepository(session)
    records = await repo.get_upcoming(pib, date.today())
    if not records:
        await callback.message.edit_text(
            f"⚠️ Графік для *{esc(pib)}* не містить змін з сьогодні\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        return

    text = format_schedule(records, pib)
    await callback.message.edit_text(
        text,
        reply_markup=kb_back_to_admin(),
        parse_mode="MarkdownV2",
    )
