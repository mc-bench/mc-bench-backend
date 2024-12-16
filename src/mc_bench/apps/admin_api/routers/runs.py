import datetime

import celery
from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from redis import StrictRedis
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import (
    StageProgress,
    TaskRetryRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    RunDetailResponse,
    RunResponse,
    RunRetryResponse,
    RunStatusResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.constants import GENERATION_STATE, RUN_STAGE_STATE, RUN_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import (
    GenerationStateChanged,
    RunStageStateChanged,
    RunStateChanged,
)
from mc_bench.models.run import Run
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_database

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
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CACHE)),
):
    run = (
        db.query(Run)
        .options(selectinload(Run.samples), selectinload(Run.artifacts))
        .filter(Run.external_id == external_id)
        .first()
    )
    return run.to_dict(
        include_samples=True, include_artifacts=True, include_stages=True, redis=redis
    )


@run_router.get(
    "/api/run/{external_id}/status",
    response_model=RunStatusResponse,
    dependencies=[
        Depends(am.require_any_scopes([PERM.RUN.ADMIN, PERM.RUN.WRITE, PERM.RUN.READ]))
    ],
)
def get_run_status(
    external_id: str,
    db: Session = Depends(get_managed_session),
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CACHE)),
):
    run = (
        db.query(Run)
        .options(selectinload(Run.samples), selectinload(Run.artifacts))
        .filter(Run.external_id == external_id)
        .first()
    )

    sort_order = [
        "PROMPT_EXECUTION",
        "RESPONSE_PARSING",
        "BUILDING",
        "EXPORTING_CONTENT",
        "POST_PROCESSING",
        "PREPARING_SAMPLE",
    ]

    return {
        "id": run.external_id,
        "status": run.state.slug,
        "stages": [
            stage.to_dict(redis=redis) for stage in run.sorted_stages(sort_order)
        ],
    }


@run_router.post(
    "/api/run/{external_id}/task-retry",
    response_model=RunRetryResponse,
    dependencies=[Depends(am.require_any_scopes([PERM.RUN.ADMIN, PERM.RUN.WRITE]))],
)
def task_retry(
    task_retry_request: TaskRetryRequest,
    external_id: str,
    db: Session = Depends(get_managed_session),
):
    run = (
        db.query(Run)
        .options(selectinload(Run.samples), selectinload(Run.artifacts))
        .filter(Run.external_id == external_id)
        .first()
    )

    emit_event(RunStateChanged(run_id=run.id, new_state=RUN_STATE.IN_RETRY))

    system_user = db.scalars(select(User).where(User.id == 1)).one()

    # Create the access token
    progress_token = am.create_access_token(
        data={
            "sub": str(system_user.external_id),
            "scopes": [
                PERM.RUN.PROGRESS_WRITE,
            ],
        },
        expires_delta=datetime.timedelta(days=2),
    )

    if run is not None:
        generation_id = run.generation_id
        sort_order = [
            "PROMPT_EXECUTION",
            "RESPONSE_PARSING",
            "BUILDING",
            "EXPORTING_CONTENT",
            "POST_PROCESSING",
            "PREPARING_SAMPLE",
        ]

        ordered_stages = run.sorted_stages(sort_order)

        if len(task_retry_request.tasks) != 1:
            raise ValueError("Bad retry")

        task_name = task_retry_request.tasks[0]
        tasks_to_retry = set(sort_order[sort_order.index(task_name) :])
        stages_to_retry = [
            stage for stage in ordered_stages if stage.stage.slug in (tasks_to_retry)
        ]

        chained_items = []
        for stage in stages_to_retry:
            if not chained_items:
                chained_items.append(
                    stage.get_task_signature(
                        app=celery,
                        progress_token=progress_token,
                        pass_args=True,
                    )
                )
            else:
                chained_items.append(
                    stage.get_task_signature(
                        app=celery,
                        progress_token=progress_token,
                        pass_args=False,
                    )
                )

            if run.generation_id is not None:
                chained_items.append(
                    celery.signature(
                        "generation.finalize_generation",
                        args=[run.generation_id],
                        queue="admin",
                        immutable=True,
                    )
                )

            emit_event(
                RunStageStateChanged(
                    stage_id=stage.id, new_state=RUN_STAGE_STATE.PENDING
                )
            )

        if generation_id is not None:
            emit_event(
                GenerationStateChanged(
                    generation_id=generation_id, new_state=GENERATION_STATE.IN_RETRY
                )
            )

        celery.chain(*chained_items).apply_async()
        return {}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown run id: {external_id}",
        )


@run_router.post(
    "/api/run/{external_id}/task/progress",
    dependencies=[Depends(am.require_any_scopes([PERM.RUN.PROGRESS_WRITE]))],
)
def set_run_progress(
    external_id: str,
    request: StageProgress,
    db: Session = Depends(get_managed_session),
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CACHE)),
):
    run = db.scalar(
        select(Run)
        .options(selectinload(Run.stages))
        .where(
            Run.external_id == external_id,
        )
    )

    run_stage = [stage for stage in run.stages if stage.stage.slug == request.stage][0]
    print(
        run_stage.id,
        run_stage.stage.slug,
        request.stage,
        request.progress,
        request.note,
    )

    run_stage.set_progress(redis, request.progress, request.note)
