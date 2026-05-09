"""Пошук графіка працівника з адмін-панелі."""

from datetime import date

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_back_to_admin
from app.services.schedule import ScheduleService
from app.states.schedule import ScheduleStates
from app.utils.schedule_formatter import format_schedule
from app.utils.text import esc

router = Router(name="admin:schedule_search")
router.message.filter(IsAdminFilter())


@router.message(StateFilter(ScheduleStates.waiting_surname), F.text)
async def receive_admin_surname(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    surname = (message.text or "").strip()
    await state.clear()

    if not surname:
        await message.answer(r"\u274c Порожне прізвище\.", parse_mode="MarkdownV2")
        return

    svc = ScheduleService(session)
    records = await svc.get_schedule_for_surname(surname, date.today())

    if not records:
        # Перевіряємо чи існує такий працівник взагалі
        from app.repositories.schedule import ScheduleRepository
        repo = ScheduleRepository(session)
        pib = await repo.find_pib_exact(surname)
        if not pib:
            await message.answer(
                f"❌ Працівника *{esc(surname)}* не знайдено\.",
                reply_markup=kb_back_to_admin(),
                parse_mode="MarkdownV2",
            )
        else:
            # Працівник є, але найближчіх змін немає (графік закінчився)
            await message.answer(
                f"⚠️ Графік для *{esc(pib)}* не містить змін з сьогодні\.",
                reply_markup=kb_back_to_admin(),
                parse_mode="MarkdownV2",
            )
        return

    # Визначаємо повне ПІБ з першого запису
    pib = records[0].pib
    text = format_schedule(records, pib)
    await message.answer(text, reply_markup=kb_back_to_admin(), parse_mode="MarkdownV2")
