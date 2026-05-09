"""Сервіс графіків — бізнес-логіка між хендлером і репозиторієм."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.schedule import ScheduleRepository


class ScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ScheduleRepository(session)

    async def import_from_rows(self, rows: list[dict]) -> int:
        """Зберігає розпарсені рядки в БД через UPSERT."""
        return await self._repo.upsert_many(rows)

    async def get_schedule_for_surname(self, surname: str, from_date) -> list:
        """Знаходить ПІБ за прізвищем і повертає найближчі зміни."""
        pib = await self._repo.find_pib_exact(surname)
        if not pib:
            return []
        return await self._repo.get_upcoming(pib, from_date)
