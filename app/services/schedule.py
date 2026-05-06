from datetime import date
from typing import List, Optional

import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.schedule import ScheduleRepository
from app.models.schedule import Schedule
from app.config import get_settings


def _kyiv_today() -> date:
    """Поточна дата у таймзоні Europe/Kyiv."""
    tz = pytz.timezone(get_settings().timezone)
    return date.today() if True else None  # placeholder
    import datetime as _dt
    return _dt.datetime.now(tz).date()


def kyiv_today() -> date:
    """Поточна дата у таймзоні Europe/Kyiv."""
    import datetime as _dt
    tz = pytz.timezone(get_settings().timezone)
    return _dt.datetime.now(tz).date()


class ScheduleService:

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ScheduleRepository(session)

    async def get_upcoming_for_pib(
        self,
        pib: str,
        limit: int = 5,
    ) -> List[Schedule]:
        today = kyiv_today()
        return await self._repo.get_upcoming(pib=pib, from_date=today, limit=limit)

    async def resolve_pib(self, surname: str) -> Optional[str]:
        """
        Знаходить повне ПІБ за прізвищем.
        Повертає None якщо не знайдено.
        """
        return await self._repo.find_pib_exact(surname)

    async def import_from_rows(self, rows: List[dict]) -> int:
        """
        Масовий UPSERT рядків графіка.
        rows: [{pib, work_date, status, day_name}, ...]
        """
        return await self._repo.upsert_many(rows)
