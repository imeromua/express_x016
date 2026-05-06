from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()

    async def exists(self, user_id: int) -> bool:
        return await self.get_by_id(user_id) is not None

    async def create(self, user_id: int, **kwargs) -> User:
        user = User(user_id=user_id, **kwargs)
        self.session.add(user)
        await self.session.flush()
        return user

    async def upsert(self, user_id: int, **kwargs) -> None:
        """INSERT або UPDATE при конфлікті по PK."""
        stmt = (
            insert(User)
            .values(user_id=user_id, **kwargs)
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={k: v for k, v in kwargs.items()},
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update(self, user_id: int, **kwargs) -> None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.session.execute(
            update(User).where(User.user_id == user_id).values(**kwargs)
        )
        await self.session.flush()

    async def set_active(self, user_id: int, is_active: bool) -> None:
        await self.update(user_id, is_active=is_active)

    async def touch(self, user_id: int) -> None:
        """Оновити last_seen_at."""
        await self.update(user_id, last_seen_at=datetime.now(timezone.utc))

    async def get_all_active(self) -> List[User]:
        result = await self.session.execute(
            select(User).where(User.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_all_active_ids(self) -> List[int]:
        result = await self.session.execute(
            select(User.user_id).where(User.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def set_role(self, user_id: int, role: str) -> None:
        await self.update(user_id, role=role)
