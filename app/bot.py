from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings


async def create_bot(token: str) -> Bot:
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def create_dispatcher(
    engine: AsyncEngine,
    redis: Redis,
    settings: Settings,
) -> Dispatcher:
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    # Передаємо залежності через workflow_data
    dp["engine"] = engine
    dp["redis"] = redis
    dp["settings"] = settings

    # Реєстрація middlewares, routers — буде у наступних кроках
    _register_middlewares(dp, engine=engine, redis=redis, settings=settings)
    _register_routers(dp)

    return dp


def _register_middlewares(dp: Dispatcher, **kwargs) -> None:
    """Placeholder — middlewares реєструються у Кроці 5."""
    pass


def _register_routers(dp: Dispatcher) -> None:
    """Placeholder — routers реєструються у Кроці 4."""
    pass
