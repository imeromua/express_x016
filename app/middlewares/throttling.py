import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message
from redis.asyncio import Redis


class ThrottlingMiddleware(BaseMiddleware):
    """
    Анти-спам через Redis.
    Ключ: throttle:{user_id}:{action}
    TTL = cooldown секунд (default 5).
    Якщо ключ існує — оғноруємо повідомлення.
    """

    def __init__(self, redis: Redis, cooldown: int = 5) -> None:
        self._redis = redis
        self._cooldown = cooldown

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        if user is None:
            return await handler(event, data)

        key = f"throttle:{user.id}:msg"
        if await self._redis.exists(key):
            # — Тихо ігноруємо; не повідомляємо юзера (щоб не спамити відповідью)
            return None

        await self._redis.setex(key, self._cooldown, "1")
        return await handler(event, data)

    @staticmethod
    async def check_action(
        redis: Redis, user_id: int, action: str, cooldown: int
    ) -> bool:
        """
        Перевіряє та записує cooldown для конкретної дії (напр., 'графік').
        Повертає True якщо дія заблокована, False якщо дозволено.
        """
        key = f"throttle:{user_id}:{action}"
        if await redis.exists(key):
            return True
        await redis.setex(key, cooldown, "1")
        return False
