from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from mc_bench.models import model_glicko_leaderboard, model
from mc_bench.database import get_session

router = APIRouter()

@router.get("/model/glicko/{metric_id}/{test_set_id}")
async def get_model_glicko_leaderboard(
    metric_id: int, test_set_id: int, db: AsyncSession = Depends(get_session)
):
    """
    Get model Glicko-2 leaderboard for a specific metric and test set.
    """
    query = (
        select(
            model_glicko_leaderboard.c.model_id,
            model.c.name.label("model_name"),
            model_glicko_leaderboard.c.glicko_rating,
            model_glicko_leaderboard.c.rating_deviation,
            model_glicko_leaderboard.c.vote_count,
            model_glicko_leaderboard.c.win_count,
            model_glicko_leaderboard.c.loss_count,
            model_glicko_leaderboard.c.tie_count,
        )
        .select_from(
            model_glicko_leaderboard.join(
                model, model_glicko_leaderboard.c.model_id == model.c.id
            )
        )
        .where(
            model_glicko_leaderboard.c.metric_id == metric_id,
            model_glicko_leaderboard.c.test_set_id == test_set_id,
        )
        .order_by(model_glicko_leaderboard.c.glicko_rating.desc())
    )

    result = await db.execute(query)
    leaderboard = result.mappings().all()
    return leaderboard 