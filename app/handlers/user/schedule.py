"""Графік — inline callbacks + reply кнопка."""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.user import kb_schedule_inline
from app.middlewares.throttling import ThrottlingMiddleware
from app.repositories.user import UserRepository
from app.services.schedule import ScheduleService
from app.states.schedule import ScheduleStates
from app.utils.text import esc

router = Router(name="user:schedule")


@router.callback_query(F.data == "schedule:my")
async def cb_my_schedule(
    callback: CallbackQuery,
    session: AsyncSession,
    redis: Redis,
) -> None:
    await callback.answer()
    user_id = callback.from_user.id

    if not await ThrottlingMiddleware.check_action(redis, user_id, "schedule", cooldown=5):
        await callback.answer("⏳ Зачекайте 5 секунд", show_alert=True)
        return

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user or not user.pib:
        await callback.message.answer(
            "⚠️ Ваш профіль не містить ПІБ\. Зв\'}яжіться з адміном\.",
            parse_mode="MarkdownV2",
        )
        return

    svc = ScheduleService(session)
    records = await svc.get_upcoming_for_pib(user.pib)

    if not records:
        await callback.message.answer(
            "📅 Графік на найближчі дні не знайдено\. Очікуйте імпорту адміном\.",
            parse_mode="MarkdownV2",
        )
        return

    from app.utils.schedule_formatter import format_schedule
    text = format_schedule(records, user.pib)
    await callback.message.answer(text, parse_mode="MarkdownV2")


@router.callback_query(F.data == "schedule:search")
async def cb_search_schedule(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    await state.set_state(ScheduleStates.waiting_surname)
    await callback.message.answer(
        "🔍 Введіть прізвище співробітника:",
    )


@router.message(StateFilter(ScheduleStates.waiting_surname), F.text)
async def receive_surname(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    redis: Redis,
) -> None:
    surname = (message.text or "").strip()
    await state.clear()

    if not surname or len(surname.split()) > 2:
        return

    if not await ThrottlingMiddleware.check_action(redis, message.from_user.id, "schedule", cooldown=5):
        await message.answer("⏳ Зачекайте 5 секунд")
        return

    svc = ScheduleService(session)
    pib = await svc.resolve_pib(surname)

    if not pib:
        await message.answer(
            f"❌ Співробітника з прізвищем *{esc(surname)}* не знайдено\.",
            parse_mode="MarkdownV2",
        )
        return

    records = await svc.get_upcoming_for_pib(pib)
    if not records:
        await message.answer("📅 Графік відсутній\.")
        return

    from app.utils.schedule_formatter import format_schedule
    text = format_schedule(records, pib)
    await message.answer(text, parse_mode="MarkdownV2")
