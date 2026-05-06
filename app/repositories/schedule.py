from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.repositories.base import BaseRepository


class ScheduleRepository(BaseRepository):

    async def upsert_many(self, rows: List[dict]) -> int:
        """
        Масовий UPSERT для імпорту з xlsx.
        rows: [{pib, work_date, status, day_name}, ...]
        Повертає кількість оброблених рядків.
        """
        if not rows:
            return 0
        stmt = (
            insert(Schedule)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_schedule_pib_date",
                set_={
                    "status": insert(Schedule).excluded.status,
                    "day_name": insert(Schedule).excluded.day_name,
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return len(rows)

    async def get_upcoming(
        self,
        pib: str,
        from_date: date,
        limit: int = 5,
    ) -> List[Schedule]:
        """
        Вибрати N записів від from_date включно.
        Використовується для команди 'Графік [Прізвище]'.
        """
        result = await self.session.execute(
            select(Schedule)
            .where(Schedule.pib == pib, Schedule.work_date >= from_date)
            .order_by(Schedule.work_date)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_pib(self, partial: str) -> List[str]:
        """
        Нечіткий пошук ПІБ (для адміна або автодоповнення).
        """
        result = await self.session.execute(
            select(Schedule.pib)
            .where(Schedule.pib.ilike(f"%{partial}%"))
            .distinct()
            .limit(10)
        )
        return list(result.scalars().all())

    async def find_pib_exact(self, surname: str) -> Optional[str]:
        """
        Знайти повне ПІБ за прізвищем (перший токен).
        Прізвище зберігається як перше слово у полі pib.
        """
        result = await self.session.execute(
            select(Schedule.pib)
            .where(Schedule.pib.ilike(f"{surname} %"))
            .distinct()
            .limit(1)
        )
        return result.scalar_one_or_none()
