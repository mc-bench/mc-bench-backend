import sqlalchemy

from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_client

from ..app import app

logger = get_logger(__name__)


@app.task(name="elo_calculation")
def elo_calculation():
    with managed_session() as db:
        logger.info("Starting elo calculation")
        db.execute(sqlalchemy.text("SELECT 1"))
        logger.info("Elo calculation completed")

    redis = get_redis_client(RedisDatabase.COMPARISON)
    try:
        logger.info("Deleting elo calculation in progress key")
        redis.delete("elo_calculation_in_progress")
        logger.info("Elo calculation in progress key deleted")
    finally:
        redis.close()

    return True
