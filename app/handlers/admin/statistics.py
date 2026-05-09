"""Statistics handler — реальна статистика по учасниках і графіку."""

from datetime import date
from typing import Optional

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_stats_menu, kb_back_to_admin
from app.models.schedule import Schedule
from app.models.user import User
from app.states.admin import AdminStates
from app.utils.text import esc

router = Router(name="admin:statistics")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


# ─── Загальна статистика ────────────────────────────────────────────────

async def get_general_stats_text(session: AsyncSession) -> str:
    today = date.today()

    total_users = (await session.execute(
        select(func.count()).select_from(User)
    )).scalar_one()
    active_users = (await session.execute(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa
    )).scalar_one()
    admin_users = (await session.execute(
        select(func.count()).select_from(User).where(User.role == "admin")
    )).scalar_one()

    total_records = (await session.execute(
        select(func.count()).select_from(Schedule)
    )).scalar_one()
    unique_employees = (await session.execute(
        select(func.count(func.distinct(Schedule.pib)))
    )).scalar_one()
    working_today = (await session.execute(
        select(func.count()).select_from(Schedule).where(
            Schedule.work_date == today, Schedule.is_working == True  # noqa
        )
    )).scalar_one()
    rest_today = (await session.execute(
        select(func.count()).select_from(Schedule).where(
            Schedule.work_date == today, Schedule.is_working == False  # noqa
        )
    )).scalar_one()
    min_date = (await session.execute(select(func.min(Schedule.work_date)))).scalar_one()
    max_date = (await session.execute(select(func.max(Schedule.work_date)))).scalar_one()

    date_str = (
        f"{esc(str(min_date))} — {esc(str(max_date))}"
        if min_date and max_date else r"_немає даних_"
    )
    today_str = esc(today.strftime("%d\.%m\.%Y"))

    return (
        f"\U0001f4ca *Статистика* \u2014 {today_str}\n\n"
        f"*👥 Користувачі*\n"
        f"• Всього в БД: *{total_users}*\n"
        f"• Активних: *{active_users}* ✅\n"
        f"• Неактивних: *{total_users - active_users}* ❌\n"
        f"• Адмінів: *{admin_users}* 🔑\n\n"
        f"*📅 Графік*\n"
        f"• Працівників у графіку: *{unique_employees}*\n"
        f"• Записів у БД: *{total_records}*\n"
        f"• Період: {date_str}\n\n"
        f"*🔹 Сьогодні*\n"
        f"• Працюють: *{working_today}* 🟢\n"
        f"• Відпочивають: *{rest_today}* ⚪\n"
    )


# ─── Статистика по працівнику ─────────────────────────────────────────

async def get_employee_stats(
    session: AsyncSession, pib: str
) -> Optional[str]:
    """SQL-агрегація по pib."""
    rows = (await session.execute(
        select(
            Schedule.pib,
            func.count().label("total"),
            func.sum(
                func.cast(Schedule.is_working == True, func.Integer())  # noqa
            ).label("work_days"),
            func.coalesce(func.sum(Schedule.shift_hours), 0).label("total_hours"),
            func.sum(
                func.cast(Schedule.status == "vacation", func.Integer())
            ).label("vacation"),
            func.sum(
                func.cast(Schedule.status == "sick", func.Integer())
            ).label("sick"),
            func.sum(
                func.cast(Schedule.status == "off", func.Integer())
            ).label("off_days"),
        )
        .where(Schedule.pib.ilike(f"%{pib}%"))
        .group_by(Schedule.pib)
        .order_by(Schedule.pib)
    )).fetchall()

    if not rows:
        return None

    results = []
    for row in rows:
        rest = (row.total or 0) - (row.work_days or 0)
        results.append(
            f"*👤 {esc(row.pib)}*\n"
            f"• Записів у графіку: *{row.total}*\n"
            f"• Робочих днів: *{row.work_days or 0}* 🟢\n"
            f"• Вихідних днів: *{row.off_days or 0}* ⚪\n"
            f"• Відпусток: *{row.vacation or 0}* 🏖\n"
            f"• Лікарняних: *{row.sick or 0}* 🏥\n"
            f"• Годин робочих: *{row.total_hours or 0}* ⏰\n"
        )

    return "\n".join(results)


# ─── Хендлери callback ───────────────────────────────────────────────

@router.callback_query(F.data == "stats:general")
async def cb_stats_general(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    text = await get_general_stats_text(session)
    await callback.message.edit_text(
        text,
        reply_markup=kb_stats_menu(),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "stats:by_employee")
async def cb_stats_by_employee(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminStates.waiting_stats_employee)
    await callback.message.edit_text(
        r"🔍 Введіть прізвище або частину ПІБ працівника:"
        r" Для виходу натисніть \/cancel\.",
        reply_markup=None,
        parse_mode="MarkdownV2",
    )


@router.message(
    StateFilter(AdminStates.waiting_stats_employee),
    F.text,
    ~F.text.startswith("/"),
)
async def receive_stats_employee(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    query = message.text.strip()
    text = await get_employee_stats(session, query)

    if not text:
        await message.answer(
            f"❌ Працівників за запитом *{esc(query)}* не знайдено\.",
            reply_markup=kb_stats_menu(),
            parse_mode="MarkdownV2",
        )
        return

    await message.answer(
        f"📊 *Статистика по працівнику*\n\n{text}",
        reply_markup=kb_stats_menu(),
        parse_mode="MarkdownV2",
    )


@router.message(
    StateFilter(AdminStates.waiting_stats_employee),
    F.text.startswith("/"),
)
async def cancel_stats_employee(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        r"❌ Скасовано\.",
        parse_mode="MarkdownV2",
    )
