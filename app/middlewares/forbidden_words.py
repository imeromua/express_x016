import json
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, TelegramObject
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.setting import SettingRepository

_CACHE_KEY = "moderation:forbidden_words"
_CACHE_TTL = 3600


class ForbiddenWordsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
        if event.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await handler(event, data)

        text = (event.text or event.caption or "").lower()
        if not text:
            return await handler(event, data)

        redis: Redis = data.get("redis")
        session: AsyncSession = data.get("session")
        if not redis or not session:
            return await handler(event, data)

        words = await self._get_words(redis, session)
        for word in words:
            if word in text:
                logger.warning(f"[forbidden] '{word}' від {event.from_user.id}")
                try:
                    await event.delete()
                    await event.bot.send_message(
                        event.from_user.id,
                        "⚠️ Твоє повідомлення видалено: містило заборонене слово\."
                        " Будь ласка, дотримуйсь правил спільноти\.",
                        parse_mode="MarkdownV2",
                    )
                except Exception as e:
                    logger.error(f"[forbidden] {e}")
                return
        return await handler(event, data)

    @staticmethod
    async def _get_words(redis: Redis, session: AsyncSession) -> list[str]:
        cached = await redis.get(_CACHE_KEY)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        repo = SettingRepository(session)
        words = await repo.get_forbidden_words()
        await redis.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(words, ensure_ascii=False))
        return words
