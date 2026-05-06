from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.enums import ChatType
from redis.asyncio import Redis

# Ключ Redis для кешу заборонених слів
_CACHE_KEY = "moderation:forbidden_words"
_CACHE_TTL = 300  # 5 хвилин


class ForbiddenWordsMiddleware(BaseMiddleware):
    """
    Перевіряє кожне повідомлення в групі на заборонені слова.
    Список кешується в Redis (TTL=5 хв).
    При срацюванні:
      1. Видаляє повідомлення
      2. Надсилає попередження юзеру в приватні
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        # Працюємо лише в групах
        if event.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await handler(event, data)

        text = (event.text or event.caption or "").lower()
        if not text:
            return await handler(event, data)

        words = await self._get_forbidden_words(data)
        matched = [w for w in words if w.lower() in text]

        if matched:
            bot = data.get("bot")
            try:
                await event.delete()
            except Exception:
                pass

            if bot and event.from_user:
                try:
                    await bot.send_message(
                        event.from_user.id,
                        f"⚠️ Твоє повідомлення було видалено, "
                        f"бо містило заборонені вирази\.
"
                        f"Будь ласка, дотримуйся правил спільноти\."    ,
                        parse_mode="MarkdownV2",
                    )
                except Exception:
                    pass
            return None  # зупиняємо обробку

        return await handler(event, data)

    async def _get_forbidden_words(self, data: Dict[str, Any]) -> List[str]:
        cached = await self._redis.get(_CACHE_KEY)
        if cached:
            import json
            return json.loads(cached)

        # Беремо з БД через сесію, яка вже в data
        session = data.get("session")
        if session is None:
            return []

        from app.repositories.setting import SettingRepository
        import json
        repo = SettingRepository(session)
        words = await repo.get_forbidden_words()
        await self._redis.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(words))
        return words
