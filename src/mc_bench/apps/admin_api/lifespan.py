from contextlib import asynccontextmanager

from mc_bench.util.postgres import get_session


@asynccontextmanager
async def lifespan():
    session = get_session()
    engine = session.bind

    yield

    engine.close()
