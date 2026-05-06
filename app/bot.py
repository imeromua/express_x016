from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings


async def create_bot(token: str) -> Bot:
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
    )


def create_dispatcher(
    engine: AsyncEngine,
    redis: Redis,
    settings: Settings,
) -> Dispatcher:
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    dp["engine"] = engine
    dp["redis"] = redis
    dp["settings"] = settings

    _register_middlewares(dp, engine=engine, redis=redis, settings=settings)
    _register_routers(dp)

    return dp


def _register_middlewares(dp: Dispatcher, **kwargs) -> None:
    """Placeholder — middlewares реєструються у Кроці 5."""
    pass


def _register_routers(dp: Dispatcher) -> None:
    from app.handlers.common.start import router as common_router
    from app.handlers.admin.router import router as admin_router
    from app.handlers.group.router import router as group_router
    from app.handlers.user.router import router as user_router

    # Порядок важливий: admin → user → group → common
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(group_router)
    dp.include_router(common_router)
