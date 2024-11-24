from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.responses import (
    RunDetailResponse,
    RunResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.run import Run
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

run_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@run_router.get(
    "/api/run",
    dependencies=[
        Depends(am.require_any_scopes([PERM.RUN.ADMIN, PERM.RUN.READ, PERM.RUN.WRITE])),
    ],
    response_model=ListResponse[RunResponse],
)
def get_runs(
    db: Session = Depends(get_managed_session),
):
    runs = list(db.scalars(select(Run)))
    payload = {
        "data": [run.to_dict() for run in runs],
        "total": len(runs),
    }

    return payload


@run_router.get(
    "/api/run/{external_id}",
    response_model=RunDetailResponse,
    dependencies=[
        Depends(am.require_any_scopes([PERM.RUN.ADMIN, PERM.RUN.WRITE, PERM.RUN.READ]))
    ],
)
def get_run(
    external_id: str,
    db: Session = Depends(get_managed_session),
):
    run = (
        db.query(Run)
        .options(selectinload(Run.samples), selectinload(Run.artifacts))
        .filter(Run.external_id == external_id)
        .first()
    )
    return run.to_dict(include_samples=True, include_artifacts=True)
