import asyncio
import logging

from loguru import logger

from app.config import get_settings
from app.bot import create_bot, create_dispatcher
from app.db.connection import create_db_engine, dispose_engine
from app.cache.connection import create_redis_pool, close_redis_pool


async def main() -> None:
    settings = get_settings()

    logging.basicConfig(level=logging.INFO)
    logger.info("🚀 Запуск бота Epicentr-Express Samar")

    engine = await create_db_engine(settings.postgres_dsn)
    redis = await create_redis_pool(settings.redis_dsn)

    bot = await create_bot(settings.bot_token)
    dp = create_dispatcher(engine=engine, redis=redis, settings=settings)

    try:
        logger.info("✅ Бот запущено. Polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("🛑 Зупинка бота...")
        await close_redis_pool(redis)
        await dispose_engine(engine)
        await bot.session.close()
        logger.info("✅ Бот зупинено.")


if __name__ == "__main__":
    asyncio.run(main())
