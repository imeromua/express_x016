"""Точка входу. Налаштовує bot, dispatcher, middleware, роутери."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_engine
from app.handlers import errors
from app.handlers.admin.router import router as admin_router
from app.handlers.group.router import router as group_router
from app.handlers.user.router import router as user_router
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.forbidden_words import ForbiddenWordsMiddleware
from app.middlewares.group_tracker import GroupTrackerMiddleware
from app.middlewares.redis import RedisMiddleware
from app.repositories.setting import SettingRepository
from app.utils.xlsx_screenshot import set_xlsx_config


# ───────────────────────────────────────────────────────────────────────────
PRINT_SEP = "─" * 60


async def _check_database(engine) -> bool:
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✅ БД підключена  │ {version[:60]}")
        return True
    except Exception as e:
        logger.error(f"❌ БД недоступна  │ {e}")
        return False


async def _check_redis(redis: Redis) -> bool:
    try:
        pong = await redis.ping()
        logger.info(f"✅ Redis підключено   │ PING → {'PONG' if pong else '???'}")
        return True
    except Exception as e:
        logger.error(f"❌ Redis недоступний  │ {e}")
        return False


async def _check_bot_token(bot: Bot) -> bool:
    try:
        me = await bot.get_me()
        logger.info(f"✅ Bot Token OK      │ @{me.username} • id={me.id}")
        return True
    except Exception as e:
        logger.error(f"❌ Bot Token хибний   │ {e}")
        return False


def _check_virustotal(settings) -> None:
    if settings.virustotal_api_key:
        masked = settings.virustotal_api_key[:6] + "****"
        logger.info(f"✅ VirusTotal API    │ ключ налаштовано ({masked})")
    else:
        logger.warning("⚠️  VirusTotal API    │ ключ не задано, перевірка відключена")


def _log_settings_summary(settings) -> None:
    admin_list = ", ".join(str(a) for a in settings.admin_ids) or "не задано"
    dsn_masked = settings.postgres_dsn.split("@")[-1] if "@" in settings.postgres_dsn else "???"
    logger.info(f"ℹ️  Група           │ id={settings.group_id}")
    logger.info(f"ℹ️  Адміни           │ {admin_list}")
    logger.info(f"ℹ️  DB DSN            │ ...@{dsn_masked}")
    logger.info(f"ℹ️  Redis URL         │ {settings.redis_url}")
    logger.info(f"ℹ️  Таймзон             │ {settings.timezone}")
    logger.info(f"ℹ️  Затримка розсилки   │ {settings.broadcast_delay}s")


async def _load_xlsx_config_on_startup(session_factory) -> None:
    async with session_factory() as session:
        repo = SettingRepository(session)
        cfg = await repo.get_xlsx_config()
        if cfg.get("xlsx_path"):
            set_xlsx_config(
                xlsx_path=cfg["xlsx_path"],
                sheet=cfg.get("xlsx_sheet"),
                cell_range=cfg.get("xlsx_cell_range"),
            )
            logger.info(f"✅ Excel config      │ {cfg['xlsx_path']}")
        else:
            logger.warning("⚠️  Excel config      │ не задано, налаштуйте через адмін-панель")


async def on_startup(bot: Bot, session_factory, redis: Redis) -> None:
    settings = get_settings()

    logger.info(PRINT_SEP)
    logger.info("🚀  EXPRESS BOT — СТАРТ")
    logger.info(PRINT_SEP)

    _log_settings_summary(settings)
    logger.info(PRINT_SEP)

    engine = get_engine()
    await _check_database(engine)
    await _check_redis(redis)
    await _check_bot_token(bot)
    _check_virustotal(settings)

    logger.info(PRINT_SEP)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Таблиці БД      │ синхронізовано")

    await _load_xlsx_config_on_startup(session_factory)

    logger.info(PRINT_SEP)
    logger.info("✅  Бот готовий, поллінг запущено")
    logger.info(PRINT_SEP)


async def on_shutdown(bot: Bot) -> None:
    logger.info(PRINT_SEP)
    logger.info("⏹️  Бот зупиняється...")
    await bot.session.close()
    engine = get_engine()
    await engine.dispose()
    logger.info("✅ Підключення закрито")
    logger.info(PRINT_SEP)


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
    # GroupTracker: реєструє кожного хто пише в групі
    dp.message.middleware(GroupTrackerMiddleware())

    # Роутери: errors перший, admin до user (фільтр IsAdmin)
    dp.include_router(errors.router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(group_router)

    async def _on_startup() -> None:
        await on_startup(bot, db_middleware.session_factory, redis)

    async def _on_shutdown() -> None:
        await on_shutdown(bot)

    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)

    # chat_member потрібен для відстеження нових учасників групи
    await dp.start_polling(
        bot,
        allowed_updates=[
            *dp.resolve_used_update_types(),
            "chat_member",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
