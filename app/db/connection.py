from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base


async def create_db_engine(dsn: str) -> AsyncEngine:
    engine = create_async_engine(
        dsn,
        echo=False,
        pool_size=10,
        max_overflow=5,
    )
    async with engine.begin() as conn:
        # Лише для dev; у продакшені — тільки Alembic
        await conn.run_sync(Base.metadata.create_all)
    return engine


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def dispose_engine(engine: AsyncEngine) -> None:
    await engine.dispose()
