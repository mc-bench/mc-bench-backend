from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.celery import send_task
from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import GenerationRequest
from mc_bench.apps.admin_api.transport_types.responses import (
    GenerationCreatedResponse,
    GenerationDetailResponse,
    GenerationResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.model import Model
from mc_bench.models.prompt import Prompt
from mc_bench.models.run import (
    GENERATION_STATE,
    Generation,
    generation_state_id_for,
)
from mc_bench.models.template import Template
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

generation_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@generation_router.post(
    "/api/run/generate",
    dependencies=[
        Depends(am.require_any_scopes([PERM.GENERATION.ADMIN, PERM.GENERATION.WRITE])),
    ],
    response_model=GenerationCreatedResponse,
)
def generate_runs(
    generation_request: GenerationRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    prompt_ids = db.scalars(
        select(Prompt.id).where(Prompt.external_id.in_(generation_request.prompt_ids))
    ).all()

    model_ids = db.scalars(
        select(Model.id).where(Model.external_id.in_(generation_request.model_ids))
    ).all()

    template_ids = db.scalars(
        select(Template.id).where(
            Template.external_id.in_(generation_request.template_ids)
        )
    ).all()

    generation = Generation(
        name=generation_request.name,
        description=generation_request.description,
        created_by=user.id,
        state_id=generation_state_id_for(db, GENERATION_STATE.CREATED),
    )
    db.add(generation)
    db.commit()  # required to ensure generation_id is present in db for runs to be created
    db.refresh(generation)

    send_task(
        "generation.create_runs",
        kwargs=dict(
            generation_id=generation.id,
            prompt_ids=prompt_ids,
            model_ids=model_ids,
            template_ids=template_ids,
        ),
    )

    generation.state_id = generation_state_id_for(db, GENERATION_STATE.IN_PROGRESS)
    db.add(generation)

    return {
        "id": generation.external_id,
    }


@generation_router.get(
    "/api/generation",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.GENERATION.ADMIN, PERM.GENERATION.READ, PERM.GENERATION.WRITE]
            )
        ),
    ],
    response_model=ListResponse[GenerationResponse],
)
def get_generations(
    db: Session = Depends(get_managed_session),
):
    generations = db.scalars(
        select(Generation).order_by(Generation.created.desc())
    ).all()
    payload = {
        "data": [
            generation.to_dict(include_runs=False, include_stats=True)
            for generation in generations
        ],
        "total": len(generations),
    }

    return payload


@generation_router.get(
    "/api/generation/{generation_id}",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.GENERATION.ADMIN, PERM.GENERATION.READ, PERM.GENERATION.WRITE]
            )
        ),
    ],
    response_model=GenerationDetailResponse,
)
def get_generation(
    generation_id: str,
    db: Session = Depends(get_managed_session),
):
    generation = db.scalar(
        select(Generation)
        .where(Generation.external_id == generation_id)
        .options(selectinload(Generation.runs))
    )

    return generation.to_dict(include_runs=True, include_stats=True)
