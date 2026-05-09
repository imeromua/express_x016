"""GroupTrackerMiddleware — автоматична реєстрація учасників групи.

При кожному повідомленні в групі робить upsert в таблицю users,
щоб адмін-панель бачила реальних учасників навіть якщо вони
ніколи не писали боту в привате.
"""

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, TelegramObject
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Awaitable, Callable, Dict

from app.config import get_settings
from app.repositories.user import UserRepository


class GroupTrackerMiddleware(BaseMiddleware):
    """Upsert user при кожному повідомленні з цільової групи."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Обробляємо лише Message з групи
        if not isinstance(event, Message):
            return await handler(event, data)

        chat_type = getattr(event.chat, "type", None)
        if chat_type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await handler(event, data)

        settings = get_settings()
        if event.chat.id != settings.group_id:
            return await handler(event, data)

        user = event.from_user
        if not user or user.is_bot:
            return await handler(event, data)

        session: AsyncSession | None = data.get("session")
        if session:
            try:
                repo = UserRepository(session)
                await repo.upsert(
                    user_id=user.id,
                    username=user.username,
                )
            except Exception as e:
                logger.warning(f"[GroupTracker] upsert error uid={user.id}: {e}")

        return await handler(event, data)
