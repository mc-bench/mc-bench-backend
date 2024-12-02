from contextlib import asynccontextmanager

from mc_bench.util.postgres import get_session
from mc_bench.util.redis import RedisDatabase, get_redis_pool


@asynccontextmanager
async def lifespan(app):
    session = get_session()
    engine = session.bind
    redis_pool = get_redis_pool(RedisDatabase.COMPARISON)

    yield

    engine.close()
    redis_pool.close()
