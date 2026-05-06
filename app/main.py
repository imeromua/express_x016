import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger
from redis.asyncio import Redis

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_engine
from app.handlers import errors
from app.handlers.admin.router import router as admin_router
from app.handlers.group.router import router as group_router
from app.handlers.user.router import router as user_router
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.forbidden_words import ForbiddenWordsMiddleware
from app.middlewares.redis import RedisMiddleware


async def on_startup(bot: Bot) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    me = await bot.get_me()
    logger.info(f"Бот запущено: @{me.username} (id={me.id})")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Бот зупиняється...")
    await bot.session.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    storage = RedisStorage(redis=redis)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
    )
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(RedisMiddleware(redis))
    dp.message.middleware(ForbiddenWordsMiddleware())

    # Роутери: errors першим, admin до user (фільтр IsAdmin)
    dp.include_router(errors.router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(group_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Поллінг запущено")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
