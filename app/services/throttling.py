"""Throttling service для команди Графік.
Обмеження: не більше 1 запиту за 5 секунд на user.
"""

from redis.asyncio import Redis


class ThrottlingService:
    @staticmethod
    async def check_action(
        redis: Redis,
        user_id: int,
        action: str,
        cooldown: int = 5,
    ) -> bool:
        """True — дозволено, False — заблоковано."""
        key = f"throttle:{action}:{user_id}"
        if await redis.get(key):
            return False
        await redis.setex(key, cooldown, "1")
        return True
