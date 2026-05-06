from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.middlewares.error import ErrorHandlerMiddleware
from app.middlewares.forbidden_words import ForbiddenWordsMiddleware


async def create_bot(token: str) -> Bot:
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
    )


def create_dispatcher(
    engine: AsyncEngine,
    redis: Redis,
    settings: Settings,
    bot: Bot | None = None,
) -> Dispatcher:
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    dp["engine"] = engine
    dp["redis"] = redis
    dp["settings"] = settings

    _register_middlewares(dp, engine=engine, redis=redis, settings=settings, bot=bot)
    _register_routers(dp)

    return dp


def _register_middlewares(
    dp: Dispatcher,
    engine: AsyncEngine,
    redis: Redis,
    settings: Settings,
    bot: Bot | None = None,
) -> None:
    error_mw = ErrorHandlerMiddleware(admin_ids=settings.admin_ids, bot=bot)

    # Усі вхідні update-евенти
    dp.update.outer_middleware(error_mw)

    # Повідомлення
    dp.message.middleware(DbSessionMiddleware(engine))
    dp.callback_query.middleware(DbSessionMiddleware(engine))

    # Throttling — легкий анти-спам на рівні message
    dp.message.middleware(ThrottlingMiddleware(redis=redis, cooldown=1))

    # Модерація: заборонені слова (тільки для групових повідомлень)
    dp.message.middleware(ForbiddenWordsMiddleware(redis=redis))


def _register_routers(dp: Dispatcher) -> None:
    from app.handlers.common.start import router as common_router
    from app.handlers.admin.router import router as admin_router
    from app.handlers.group.router import router as group_router
    from app.handlers.user.router import router as user_router

    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(group_router)
    dp.include_router(common_router)
