"""Пошук графіка працівника з адмін-панелі."""

from datetime import date

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_back_to_admin
from app.repositories.schedule import ScheduleRepository
from app.services.schedule import ScheduleService
from app.states.schedule import ScheduleStates
from app.utils.schedule_formatter import format_schedule
from app.utils.text import esc

router = Router(name="admin:schedule_search")
router.message.filter(IsAdminFilter())

# Тексти Reply-кнопок адмінки — не вважати ємністю прізвища
_ADMIN_BUTTON_TEXTS = {
    "📢 розсилка", "📂 імпорт графіка",
    "🚫 стоп-слова", "📊 статистика",
    "📅 графік працівника", "⚙️ налаштування excel",
}


@router.message(StateFilter(ScheduleStates.waiting_surname), F.text)
async def receive_admin_surname(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    surname = (message.text or "").strip()

    # Ігноруємо натискання Reply-кнопок адмінки
    if surname.lower() in _ADMIN_BUTTON_TEXTS:
        await state.clear()
        return

    if not surname:
        await state.clear()
        await message.answer(r"❌ Порожне прізвище\.", parse_mode="MarkdownV2")
        return

    await state.clear()

    repo = ScheduleRepository(session)
    pib = await repo.find_pib_exact(surname)

    if not pib:
        await message.answer(
            f"❌ Працівника *{esc(surname)}* не знайдено\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        return

    records = await repo.get_upcoming(pib, date.today())
    if not records:
        await message.answer(
            f"⚠️ Графік для *{esc(pib)}* не містить змін з сьогодні\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        return

    text = format_schedule(records, pib)
    await message.answer(text, reply_markup=kb_back_to_admin(), parse_mode="MarkdownV2")
