from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_upcoming(
        self, pib: str, from_date: date, limit: int = 7
    ) -> List[Schedule]:
        result = await self._s.execute(
            select(Schedule)
            .where(Schedule.pib == pib, Schedule.work_date >= from_date)
            .order_by(Schedule.work_date)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_pib_exact(self, surname: str) -> Optional[str]:
        """
        Знаходить повне ПІБ за прізвищем (перший токен, case-insensitive).
        Повертає None якщо не знайдено.
        """
        result = await self._s.execute(
            select(Schedule.pib)
            .where(Schedule.pib.ilike(f"{surname}%"))
            .order_by(Schedule.pib)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert_many(self, rows: list[dict]) -> int:
        """Масовий UPSERT. Повертає кількість оброблених рядків."""
        if not rows:
            return 0
        stmt = (
            insert(Schedule)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["pib", "work_date"],
                set_={
                    "status": insert(Schedule).excluded.status,
                    "day_name": insert(Schedule).excluded.day_name,
                    "is_working": insert(Schedule).excluded.is_working,
                    "shift_hours": insert(Schedule).excluded.shift_hours,
                },
            )
        )
        await self._s.execute(stmt)
        await self._s.commit()
        return len(rows)
