import datetime

from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.auth.permissions import PERM
from mc_bench.constants import GENERATION_STATE, EXPERIMENTAL_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import GenerationStateChanged
from mc_bench.models.log import SampleApproval
from mc_bench.models.model import Model
from mc_bench.models.prompt import Prompt
from mc_bench.models.run import (
    Generation,
    TestSet,
    SampleApprovalState,
    generation_state_id_for,
    experimental_state_id_for,
)
from mc_bench.models.sample import Sample
from mc_bench.models.template import Template
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

from .. import celery
from ..config import settings
from ..transport_types.generic import ListResponse
from ..transport_types.requests import GenerationRequest, BulkSampleApprovalRequest
from ..transport_types.responses import (
    BulkSampleApprovalResponse,
    GenerationCreatedResponse,
    GenerationDetailResponse,
    GenerationResponse,
)

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

    default_test_set_id = None

    if generation_request.default_test_set_id is not None:
        default_test_set = db.scalars(
            select(TestSet).where(
                TestSet.external_id == generation_request.default_test_set_id
            )
        ).one()
        default_test_set_id = default_test_set.id

    generation = Generation(
        name=generation_request.name,
        description=generation_request.description,
        created_by=user.id,
        state_id=generation_state_id_for(db, GENERATION_STATE.CREATED),
        default_test_set_id=default_test_set_id,
    )
    db.add(generation)
    db.commit()  # required to ensure generation_id is present in db for runs to be created
    db.refresh(generation)

    system_user = db.scalars(select(User).where(User.id == 1)).one()

    # Create the access token
    progress_token = am.create_access_token(
        data={
            "sub": str(system_user.external_id),
            "scopes": [
                # Permits the bearer to write run progress updates
                PERM.RUN.PROGRESS_WRITE,
                # Permits the bearer to retry runs
                PERM.RUN.ADMIN,  # TODO: Make a standalone retry permission
            ],
        },
        expires_delta=datetime.timedelta(days=2),
    )

    celery.create_runs(
        generation_id=generation.id,
        prompt_ids=prompt_ids,
        model_ids=model_ids,
        template_ids=template_ids,
        num_samples=generation_request.num_samples,
        progress_token=progress_token,
    )

    emit_event(
        GenerationStateChanged(
            generation_id=generation.id, new_state=GENERATION_STATE.IN_PROGRESS
        )
    )

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

    return generation.to_dict(include_runs=False, include_stats=True)


@generation_router.post(
    "/api/generation/{generation_id}/approve-samples",
    dependencies=[
        Depends(am.require_any_scopes([PERM.VOTING.ADMIN])),
    ],
    response_model=BulkSampleApprovalResponse
)
def approve_all_samples(
    generation_id: str,
    approval_request: BulkSampleApprovalRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    
    # Get the user
    try:
        user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Find the generation
    generation = db.scalar(
        select(Generation)
        .where(Generation.external_id == generation_id)
        .options(selectinload(Generation.runs))
    )
    
    if not generation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Generation with ID {generation_id} not found")
    
    # Get the test set
    try:
        test_set = db.scalars(
            select(TestSet).where(TestSet.external_id == approval_request.test_set_id)
        ).one()
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Test set with ID {approval_request.test_set_id} not found")
    
    # Get all run IDs for this generation
    run_ids = [run.id for run in generation.runs]
    
    # Find all eligible samples
    eligible_samples = db.scalars(
        select(Sample)
        .where(
            Sample.run_id.in_(run_ids),
            Sample.is_complete == True,
            Sample.experimental_state_id == experimental_state_id_for(db, EXPERIMENTAL_STATE.RELEASED),
            Sample.approval_state == None
        )
    ).all()
    
    approved_state = db.scalar(
        select(SampleApprovalState).where(SampleApprovalState.name == "APPROVED")
    )
    
    if not approved_state:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to find approval state")
    
    # Approve all eligible samples
    for sample in eligible_samples:
        sample.approval_state = approved_state
        sample.test_set_id = test_set.id
        
        # Create sample approval log entry
        approval = SampleApproval(
            sample=sample,
            user=user,
            test_set=test_set,
            note=approval_request.note if approval_request.note else None,
        )
        db.add(approval)
    
    db.commit()
    
    # Count remaining pending samples
    remaining_pending = db.scalar(
        select(db.func.count())
        .select_from(Sample)
        .where(
            Sample.run_id.in_(run_ids),
            Sample.is_complete == True,
            Sample.experimental_state_id == experimental_state_id_for(db, EXPERIMENTAL_STATE.RELEASED),
            Sample.approval_state == None
        )
    )
    
    return {
        "total_approved": len(eligible_samples),
        "remaining_pending": remaining_pending,
    }
