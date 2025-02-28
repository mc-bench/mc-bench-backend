import datetime
from typing import List, Optional
from uuid import UUID

import celery
from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from redis import StrictRedis
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.requests import (
    StageProgress,
    TaskRetryRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    PagedListResponse,
    RunDetailResponse,
    RunResponse,
    RunRetryResponse,
    RunStagesResponse,
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
from mc_bench.models.model import Model
from mc_bench.models.prompt import Prompt
from mc_bench.models.run import (
    Generation,
    Run,
    RunStage,
    Stage,
    run_stage_state_id_for,
    run_state_id_for,
)
from mc_bench.models.template import Template
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_database

from ..celery import celery as celery_app

logger = get_logger(__name__)

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
    response_model=PagedListResponse[RunResponse],
)
def get_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    model_id: Optional[List[UUID]] = Query(None),
    template_id: Optional[List[UUID]] = Query(None),
    prompt_id: Optional[List[UUID]] = Query(None),
    generation_id: Optional[List[UUID]] = Query(None),
    state: Optional[List[str]] = Query(None),
    completed_stage: Optional[List[str]] = Query(None),
    in_progress_stage: Optional[List[str]] = Query(None),
    username: Optional[str] = Query(None),
    db: Session = Depends(get_managed_session),
    current_scopes: List[str] = Depends(am.current_scopes),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    if PERM.RUN.ADMIN in current_scopes or PERM.RUN.READ in current_scopes:
        # Basic permissions - allow global access with username filter
        if username:
            filtered_user = db.scalars(
                select(User).where(User.username == username)
            ).first()
            if not filtered_user:
                return {
                    "data": [],
                    "paging": {
                        "page": page,
                        "pageSize": page_size,
                        "totalPages": 0,
                        "totalItems": 0,
                        "hasNext": False,
                        "hasPrevious": False,
                    },
                }
            query = (
                select(Run)
                .order_by(Run.created.desc())
                .where(Run.creator == filtered_user)
            )
        else:
            query = select(Run).order_by(Run.created.desc())
    else:
        # Limited permissions - only see own runs
        query = select(Run).order_by(Run.created.desc()).where(Run.creator == user)

    # Apply filters
    if model_id:
        query = query.join(Run.model).filter(Model.external_id.in_(model_id))

    if template_id:
        query = query.join(Run.template).filter(Template.external_id.in_(template_id))

    if prompt_id:
        query = query.join(Run.prompt).filter(Prompt.external_id.in_(prompt_id))

    if generation_id:
        query = query.join(Run.generation).filter(
            Generation.external_id.in_(generation_id)
        )

    # Update state filter to use the state_slug column
    if state:
        state_ids = [
            run_state_id_for(db, RUN_STATE(state_element)) for state_element in state
        ]
        query = query.filter(Run.state_id.in_(state_ids))

    # Add filter for completed stages
    if completed_stage:
        for stage_name in completed_stage:
            # For each completed stage, add a join to find runs with that stage completed
            stage_subquery = (
                select(Stage.id).where(Stage.slug == stage_name).scalar_subquery()
            )
            completed_state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)

            # Create a correlated subquery that properly links to the current Run
            run_stage_alias = (
                db.query(RunStage)
                .filter(
                    RunStage.run_id == Run.id,  # Important: Link to the current Run
                    RunStage.stage_id == stage_subquery,
                    RunStage.state_id == completed_state_id,
                )
                .exists()
            )
            query = query.filter(run_stage_alias)

    # Add filter for in-progress stages
    if in_progress_stage:
        for stage_name in in_progress_stage:
            # For each in-progress stage, add a join to find runs with that stage in progress
            stage_subquery = (
                select(Stage.id).where(Stage.slug == stage_name).scalar_subquery()
            )
            in_progress_state_id = run_stage_state_id_for(
                db, RUN_STAGE_STATE.IN_PROGRESS
            )

            # Create a correlated subquery that properly links to the current Run
            run_stage_alias = (
                db.query(RunStage)
                .filter(
                    RunStage.run_id == Run.id,  # Important: Link to the current Run
                    RunStage.stage_id == stage_subquery,
                    RunStage.state_id == in_progress_state_id,
                )
                .exists()
            )
            query = query.filter(run_stage_alias)

    # Execute query and handle pagination
    total = db.scalar(select(func.count()).select_from(query.subquery()))

    query = (
        query.order_by(Run.created.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    runs = db.scalars(query).all()

    return {
        "data": [run.to_dict() for run in runs],
        "paging": {
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "totalItems": total,
            "hasNext": page * page_size < total,
            "hasPrevious": page > 1,
        },
    }


@run_router.get(
    "/api/run/stages",
    dependencies=[
        Depends(am.require_any_scopes([PERM.RUN.ADMIN, PERM.RUN.READ, PERM.RUN.WRITE])),
    ],
    response_model=RunStagesResponse,
)
def get_run_stages(
    db: Session = Depends(get_managed_session),
):
    """Get all possible run stages for filtering."""
    stages = db.scalars(select(Stage).order_by(Stage.slug)).all()
    return {
        "data": [stage.slug for stage in stages],
    }


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
    current_scopes: List[str] = Depends(am.current_scopes),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    query = (
        db.query(Run)
        .options(selectinload(Run.samples), selectinload(Run.artifacts))
        .filter(Run.external_id == external_id)
    )

    if PERM.RUN.ADMIN in current_scopes or PERM.RUN.READ in current_scopes:
        run = query.first()
    else:
        run = query.where(Run.creator == user).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown run id: {external_id}",
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
        "CODE_VALIDATION",
        "BUILDING",
        "RENDERING_SAMPLE",
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
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CACHE)),
    current_scopes: List[str] = Depends(am.current_scopes),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    run = (
        db.query(Run)
        .options(selectinload(Run.samples), selectinload(Run.artifacts))
        .filter(Run.external_id == external_id)
    )

    if PERM.RUN.ADMIN in current_scopes or PERM.RUN.WRITE in current_scopes:
        run = run.first()
    else:
        run = run.where(Run.creator == user).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown run id: {external_id}",
        )

    emit_event(RunStateChanged(run_id=run.id, new_state=RUN_STATE.IN_RETRY))

    emit_event(RunStateChanged(run_id=run.id, new_state=RUN_STATE.IN_RETRY))

    system_user = db.scalars(select(User).where(User.id == 1)).one()

    # Create the access token
    progress_token = am.create_access_token(
        data={
            "sub": str(system_user.external_id),
            "scopes": [
                PERM.RUN.PROGRESS_WRITE,
                PERM.RUN.ADMIN,
            ],
        },
        expires_delta=datetime.timedelta(days=2),
    )

    if run is not None:
        generation_id = run.generation_id
        sort_order = [
            "PROMPT_EXECUTION",
            "RESPONSE_PARSING",
            "CODE_VALIDATION",
            "BUILDING",
            "RENDERING_SAMPLE",
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
            stage.set_progress(redis, 0, None)
            if not chained_items:
                chained_items.append(
                    stage.get_task_signature(
                        app=celery_app,
                        progress_token=progress_token,
                        pass_args=True,
                    )
                )
            else:
                chained_items.append(
                    stage.get_task_signature(
                        app=celery_app,
                        progress_token=progress_token,
                        pass_args=False,
                    )
                )

            emit_event(
                RunStageStateChanged(
                    stage_id=stage.id, new_state=RUN_STAGE_STATE.PENDING
                )
            )

        # TODO: This is a hack to not set sample pending if we are about to generate a new sample
        if run.samples and task_name != "PROMPT_EXECUTION":
            sample = run.samples[-1]
            sample.is_pending = True
            sample.is_complete = False
            db.add(sample)
            db.commit()

        tasks = celery.chain(*chained_items)

        if generation_id is not None:
            emit_event(
                GenerationStateChanged(
                    generation_id=generation_id, new_state=GENERATION_STATE.IN_RETRY
                )
            )

        tasks.apply_async()
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
    run_stage.set_progress(redis, request.progress, request.note)
