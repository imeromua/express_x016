"""Пошук графіка працівника з адмін-панелі.
Використовує той самий ScheduleStates.waiting_surname що і group triggers.
"""

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
        await message.answer("❌ Порожне прізвище\.", parse_mode="MarkdownV2")
        return

    svc = ScheduleService(session)
    pib = await svc.resolve_pib(surname)

    if not pib:
        await message.answer(
            f"❌ Працівника *{esc(surname)}* не знайдено\.",
            reply_markup=kb_back_to_admin(),
            parse_mode="MarkdownV2",
        )
        return

    records = await svc.get_upcoming_for_pib(pib)
    text = format_schedule(records, pib)
    await message.answer(text, reply_markup=kb_back_to_admin(), parse_mode="MarkdownV2")
