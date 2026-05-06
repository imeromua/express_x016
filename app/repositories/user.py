from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert(self, **kwargs) -> User:
        stmt = (
            insert(User)
            .values(**kwargs)
            .on_conflict_do_update(
                index_elements=[User.user_id],
                set_={k: v for k, v in kwargs.items() if k != "user_id"},
            )
            .returning(User)
        )
        result = await self._s.execute(stmt)
        await self._s.commit()
        return result.scalar_one()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self._s.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        """Пошук за нормалізованим номером телефону."""
        result = await self._s.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()

    async def get_all_active_ids(self) -> List[int]:
        result = await self._s.execute(
            select(User.user_id).where(User.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def set_active(self, user_id: int, active: bool) -> None:
        await self._s.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(is_active=active)
        )
        await self._s.commit()

    async def count_active(self) -> int:
        from sqlalchemy import func
        result = await self._s.execute(
            select(func.count()).select_from(User).where(User.is_active == True)  # noqa
        )
        return result.scalar_one()
