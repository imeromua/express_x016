"""GroupTrackerMiddleware — автоматична реєстрація учасників групи.

При кожному повідомленні в групі робить upsert в таблицю users,
щоб адмін-панель бачила реальних учасників навіть якщо вони
ніколи не писали боту в привате.
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, TelegramObject
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

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
        # Обробляємо лише Message
        if not isinstance(event, Message):
            return await handler(event, data)

        chat_type = getattr(event.chat, "type", None)
        chat_id = getattr(event.chat, "id", None)

        # Діагностика: логуємо кожне повідомлення
        user = event.from_user
        uname = f"@{user.username}" if user and user.username else str(getattr(user, 'id', '?'))
        logger.debug(
            f"[GroupTracker] msg chat_type={chat_type} chat_id={chat_id} "
            f"from={uname} is_bot={getattr(user, 'is_bot', '?')}"
        )

        if chat_type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            logger.debug(f"[GroupTracker] пропуск: не група (chat_type={chat_type})")
            return await handler(event, data)

        settings = get_settings()
        expected_id = int(settings.group_id)  # захищаємо від типу str vs int

        if chat_id != expected_id:
            logger.debug(
                f"[GroupTracker] пропуск: чужа група "
                f"chat_id={chat_id} != expected={expected_id}"
            )
            return await handler(event, data)

        if not user or user.is_bot:
            logger.debug(f"[GroupTracker] пропуск: bot або без from_user")
            return await handler(event, data)

        session: AsyncSession | None = data.get("session")
        if not session:
            logger.warning("[GroupTracker] session недоступна в data")
            return await handler(event, data)

        try:
            repo = UserRepository(session)
            await repo.upsert(user_id=user.id, username=user.username)
            logger.info(
                f"[GroupTracker] ✅ upsert uid={user.id} "
                f"{uname} в чаті {chat_id}"
            )
        except Exception as e:
            logger.warning(f"[GroupTracker] upsert error uid={user.id}: {e}")

        return await handler(event, data)
