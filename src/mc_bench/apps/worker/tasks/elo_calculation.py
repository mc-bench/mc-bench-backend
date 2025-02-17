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

        # we need a leaderboard table
        # we need a tie flag and a processed flag
        # eventually need a partial index on comparison table

        # get earliest unprocesseed rows (lock for update)
        latest_timestamp = get_latest_unprocessed_rows(db)  # <- will look at index
        rows = get_unprocessed_rows(db, batch_size=1000)    # <- will look at index

        if rows:
            leaderboard = get_leaderboard_rows(db) # lock for update

            for row in rows:
                update_leaderboard(db, leaderboard, row)

                # get current leaderboard scores (probably lock for writes)
                # DO IN PYTHON
                # Update leaderboard
                # Update with processed flag
            write_leader_leaderboard(db, leaderboard)
            mark_rows_as_processed(db, rows)
    
    # implicit commit


    redis = get_redis_client(RedisDatabase.COMPARISON)
    try:
        logger.info("Deleting elo calculation in progress key")
        redis.delete("elo_calculation_in_progress")
        logger.info("Elo calculation in progress key deleted")
    finally:
        redis.close()

    return True
