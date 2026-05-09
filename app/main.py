"""Точка входу. Налаштуває bot, dispatcher, middleware, роутери."""

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
from app.repositories.setting import SettingRepository
from app.utils.xlsx_screenshot import set_xlsx_config


async def _load_xlsx_config_on_startup(session_factory) -> None:
    """Завантажує налаштування Excel з БД при старті."""
    async with session_factory() as session:
        repo = SettingRepository(session)
        cfg = await repo.get_xlsx_config()
        if cfg.get("xlsx_path"):
            set_xlsx_config(
                xlsx_path=cfg["xlsx_path"],
                sheet=cfg.get("xlsx_sheet"),
                cell_range=cfg.get("xlsx_cell_range"),
            )
            logger.info(f"[startup] Excel config loaded: {cfg}")
        else:
            logger.warning("[startup] Excel config not set. Use admin panel to configure.")


async def on_startup(bot: Bot, session_factory) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _load_xlsx_config_on_startup(session_factory)
    me = await bot.get_me()
    logger.info(f"Бот запущено: @{me.username} (id={me.id})")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Бот зупиняється...")
    await bot.session.close()
    
    engine = get_engine()
    await engine.dispose()
    logger.info("Підключення до бази даних закрито")


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
    db_middleware = DbSessionMiddleware()
    dp.update.middleware(db_middleware)
    dp.update.middleware(RedisMiddleware(redis))
    dp.message.middleware(ForbiddenWordsMiddleware())

    # Роутери: errors перший, admin до user (фільтр IsAdmin)
    dp.include_router(errors.router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(group_router)

    dp.startup.register(lambda: on_startup(bot, db_middleware.session_factory))
    dp.shutdown.register(lambda: on_shutdown(bot))

    logger.info("Поллінг запущено")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
