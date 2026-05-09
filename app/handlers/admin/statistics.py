"""Statistics handler — реальна статистика по учасниках і графіку."""

from datetime import date

from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.models.user import User
from app.utils.text import esc


async def get_stats_text(session: AsyncSession) -> str:
    today = date.today()

    # ── Users ────────────────────────────────────────────────
    total_users = (await session.execute(
        select(func.count()).select_from(User)
    )).scalar_one()

    active_users = (await session.execute(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa
    )).scalar_one()

    inactive_users = total_users - active_users

    admin_users = (await session.execute(
        select(func.count()).select_from(User).where(User.role == "admin")
    )).scalar_one()

    # ── Schedule ────────────────────────────────────────────
    total_records = (await session.execute(
        select(func.count()).select_from(Schedule)
    )).scalar_one()

    unique_employees = (await session.execute(
        select(func.count(func.distinct(Schedule.pib)))
    )).scalar_one()

    working_today = (await session.execute(
        select(func.count()).select_from(Schedule).where(
            Schedule.work_date == today,
            Schedule.is_working == True,  # noqa
        )
    )).scalar_one()

    rest_today = (await session.execute(
        select(func.count()).select_from(Schedule).where(
            Schedule.work_date == today,
            Schedule.is_working == False,  # noqa
        )
    )).scalar_one()

    # Найранніша дата графіка
    min_date = (await session.execute(
        select(func.min(Schedule.work_date))
    )).scalar_one()
    max_date = (await session.execute(
        select(func.max(Schedule.work_date))
    )).scalar_one()

    date_str = (
        f"{esc(str(min_date))} — {esc(str(max_date))}"
        if min_date and max_date else r"_немає даних_"
    )

    today_str = esc(today.strftime("%d\.%m\.%Y"))

    text = (
        f"\U0001f4ca *Статистика* \u2014 {today_str}\n"
        f"\n"
        f"*👥 Користувачі*\n"
        f"• Всього в БД: *{total_users}*\n"
        f"• Активних: *{active_users}* ✅\n"
        f"• Неактивних: *{inactive_users}* ❌\n"
        f"• Адмінів: *{admin_users}* 🔑\n"
        f"\n"
        f"*📅 Графік*\n"
        f"• Працівників у графіку: *{unique_employees}*\n"
        f"• Записів у БД: *{total_records}*\n"
        f"• Період: {date_str}\n"
        f"\n"
        f"*🔹 Сьогодні*\n"
        f"• Працюють: *{working_today}* 🟢\n"
        f"• Відпочивають: *{rest_today}* ⚪\n"
    )
    return text
