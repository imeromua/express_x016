from redis.asyncio import Redis, ConnectionPool


async def create_redis_pool(dsn: str) -> Redis:
    pool = ConnectionPool.from_url(dsn, decode_responses=True)
    redis = Redis(connection_pool=pool)
    await redis.ping()
    return redis


async def close_redis_pool(redis: Redis) -> None:
    await redis.aclose()
