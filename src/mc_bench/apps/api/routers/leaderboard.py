from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from mc_bench.util.postgres import get_managed_session
from mc_bench.models.run import Run
from mc_bench.models.model import Model
# from mc_bench.auth.permissions import PERM
# from mc_bench.server.auth import AuthManager
from ..config import settings

leaderboard_router = APIRouter(prefix="/api")

# Do we need auth for this?
# am = AuthManager(
#     jwt_secret=settings.JWT_SECRET_KEY,
#     jwt_algorithm=settings.ALGORITHM,
# )

@leaderboard_router.get(
    "/leaderboard",
    tags=["leaderboard"],
    summary="Get model leaderboard",
    description="Returns a list of models with their run statistics, sorted by success rate"
)
def get_leaderboard(db: Session = Depends(get_managed_session)):
    # Get total runs and success count per model
    stats = (
        db.execute(
            select(
                Model.slug,
                func.count(Run.id).label('total_runs'),
                func.count(Run.id).filter(Run.state_id == 4).label('successful_runs')
            )
            .join(Run)
            .group_by(Model.slug)
        ).all()
    )

    # Convert to simple dict format
    leaderboard = [
        {
            "model": row.slug,
            "total_runs": row.total_runs,
            "successful_runs": row.successful_runs,
            "success_rate": round(row.successful_runs / row.total_runs * 100, 2) if row.total_runs > 0 else 0
        }
        for row in stats
    ]

    # Sort by success rate descending
    leaderboard.sort(key=lambda x: x["success_rate"], reverse=True)
    
    return leaderboard

# Sample response
# isaac@Mac mc-bench-backend % curl http://localhost:8000/api/leaderboard
# [{"model":"grok-2-1212","total_runs":1,"successful_runs":0,"success_rate":0.0},{"model":"claude-3-5-sonnet-20241022","total_runs":1,"successful_runs":0,"success_rate":0.0},{"model":"gpt-4o-2024-11-20","total_runs":1,"successful_runs":0,"success_rate":0.0}]%