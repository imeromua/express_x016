"""Statistics handler — реальна статистика по учасниках і графіку."""

from datetime import date
from typing import Optional

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import Integer, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_stats_menu, kb_pib_picker
from app.models.schedule import Schedule
from app.models.user import User
from app.repositories.schedule import ScheduleRepository
from app.states.admin import AdminStates
from app.utils.text import esc

router = Router(name="admin:statistics")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

_STATS_PIB_PREFIX = "stats_pib"


# ─── Загальна статистика ────────────────────────────────────────────────

async def get_general_stats_text(session: AsyncSession) -> str:
    today = date.today()
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    active_users = (await session.execute(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa
    )).scalar_one()
    admin_users = (await session.execute(
        select(func.count()).select_from(User).where(User.role == "admin")
    )).scalar_one()
    total_records = (await session.execute(select(func.count()).select_from(Schedule))).scalar_one()
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
    today_str = esc(today.strftime("%d.%m.%Y"))
    return (
        f"📊 *Статистика* — {today_str}\n\n"
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


async def get_employee_stats_by_pib(session: AsyncSession, pib: str) -> str:
    rows = (await session.execute(
        select(
            Schedule.pib,
            func.count().label("total"),
            func.sum(case((Schedule.is_working == True, 1), else_=0)).label("work_days"),  # noqa
            func.coalesce(func.sum(Schedule.shift_hours), 0).label("total_hours"),
            func.sum(case((Schedule.status == "vacation", 1), else_=0)).label("vacation"),
            func.sum(case((Schedule.status == "sick", 1), else_=0)).label("sick"),
            func.sum(case((Schedule.status == "off", 1), else_=0)).label("off_days"),
        )
        .where(Schedule.pib == pib)
        .group_by(Schedule.pib)
    )).fetchone()

    if not rows:
        return f"❌ Даних для *{esc(pib)}* не знайдено\."

    return (
        f"*👤 {esc(rows.pib)}*\n"
        f"• Записів у графіку: *{rows.total}*\n"
        f"• Робочих днів: *{rows.work_days or 0}* 🟢\n"
        f"• Вихідних днів: *{rows.off_days or 0}* ⚪\n"
        f"• Відпусток: *{rows.vacation or 0}* 🏖\n"
        f"• Лікарняних: *{rows.sick or 0}* 🏥\n"
        f"• Годин робочих: *{rows.total_hours or 0}* ⏰\n"
    )


# ─── Калбеки ──────────────────────────────────────────────────

@router.callback_query(F.data == "stats:general")
async def cb_stats_general(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    text = await get_general_stats_text(session)
    await callback.message.edit_text(text, reply_markup=kb_stats_menu(), parse_mode="MarkdownV2")


@router.callback_query(F.data == "stats:by_employee")
async def cb_stats_by_employee(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    repo = ScheduleRepository(session)
    pib_list = await repo.get_all_unique_pib()

    if not pib_list:
        await callback.answer("⚠️ Графік порожній", show_alert=True)
        return

    kb = kb_pib_picker(
        pib_list=pib_list,
        callback_prefix=_STATS_PIB_PREFIX,
        page=0,
        back_cb="stats:general",
    )
    await callback.message.edit_text(
        "👤 Оберіть працівника:",
        reply_markup=kb,
    )


@router.callback_query(F.data.regexp(rf"^{_STATS_PIB_PREFIX}:page:(\d+)$"))
async def cb_stats_pib_page(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    page = int(callback.data.split(":")[2])
    repo = ScheduleRepository(session)
    pib_list = await repo.get_all_unique_pib()
    kb = kb_pib_picker(
        pib_list=pib_list,
        callback_prefix=_STATS_PIB_PREFIX,
        page=page,
        back_cb="stats:general",
    )
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(F.data.regexp(rf"^{_STATS_PIB_PREFIX}:(?!page:).+$"))
async def cb_stats_pib_select(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    pib = callback.data[len(_STATS_PIB_PREFIX) + 1:]
    text = await get_employee_stats_by_pib(session, pib)
    await callback.message.edit_text(
        f"📊 *Статистика по працівнику*\n\n{text}",
        reply_markup=kb_stats_menu(),
        parse_mode="MarkdownV2",
    )
