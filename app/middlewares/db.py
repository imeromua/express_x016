from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession


class DbSessionMiddleware(BaseMiddleware):
    """
    Передає в хендлер відкриту сесію `session`.
    Автоматичний commit після хендлера, rollback при помилці.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._factory = async_sessionmaker(engine, expire_on_commit=False)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self._factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
