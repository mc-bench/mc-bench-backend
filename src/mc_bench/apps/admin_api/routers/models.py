import json
from typing import List, Optional, Union

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import mc_bench.schema.postgres as schema
from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import (
    CreateModelRequest,
    ModelExperimentalStateApprovalRequest,
    ModelExperimentalStateProposalRequest,
    ModelExperimentalStateRejectionRequest,
    ModelObservationRequest,
    UpdateModelRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    ExperimentalStateResponse,
    ModelCreatedResponse,
    ModelDetailResponse,
    ModelResponse,
    ProviderClassResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.constants import EXPERIMENTAL_STATE
from mc_bench.models.experimental_state import (
    ExperimentalState,
    experimental_state_id_for,
)
from mc_bench.models.log import (
    ExperimentalStateApproval,
    ExperimentalStateProposal,
    ExperimentalStateRejection,
    ModelObservation,
)
from mc_bench.models.model import Model, ModelExperimentalStateProposal, ProviderClass
from mc_bench.models.provider import Provider
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session

logger = get_logger(__name__)

model_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@model_router.get(
    "/api/provider-class",
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.READ, PERM.MODEL.WRITE])
        ),
    ],
    response_model=List[ProviderClassResponse],
)
def get_provider_class(
    db: Session = Depends(get_managed_session),
):
    return [
        provider_class.to_dict() for provider_class in db.scalars(select(ProviderClass))
    ]


@model_router.get(
    "/api/model",
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.READ, PERM.MODEL.WRITE])
        ),
    ],
    response_model=ListResponse[ModelResponse],
)
def get_models(
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
    current_scopes=Depends(am.current_scopes),
    has_observations: Optional[bool] = None,
    has_pending_proposals: Optional[bool] = None,
    active: Optional[bool] = None,
    experimental_states: Optional[List[str]] = Query(None),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    # Create a subquery to get observation counts in bulk
    observation_counts = (
        select(
            schema.research.model_log.c.model_id.label("model_id"),
            func.count().label("observation_count"),
        )
        .select_from(schema.research.model_log)
        .join(
            schema.research.log,
            schema.research.model_log.c.log_id == schema.research.log.c.id,
        )
        .join(
            schema.research.note,
            schema.research.log.c.note_id == schema.research.note.c.id,
        )
        .where(schema.research.note.c.kind_slug == "OBSERVATION")
        .group_by(schema.research.model_log.c.model_id)
        .subquery()
    )

    # Create a subquery to get pending proposal counts in bulk
    pending_proposal_counts = (
        select(
            schema.research.model_experimental_state_proposal.c.model_id.label(
                "model_id"
            ),
            func.count().label("proposal_count"),
        )
        .select_from(schema.research.model_experimental_state_proposal)
        .where(
            (
                schema.research.model_experimental_state_proposal.c.accepted.is_(None)
                | (
                    schema.research.model_experimental_state_proposal.c.accepted
                    == False
                )
            ),
            (
                schema.research.model_experimental_state_proposal.c.rejected.is_(None)
                | (
                    schema.research.model_experimental_state_proposal.c.rejected
                    == False
                )
            ),
        )
        .group_by(schema.research.model_experimental_state_proposal.c.model_id)
        .subquery()
    )

    # Build the base query with the left joins to include models with zero counts
    base_query = (
        select(
            Model,
            func.coalesce(observation_counts.c.observation_count, 0).label(
                "note_count"
            ),
            func.coalesce(pending_proposal_counts.c.proposal_count, 0).label(
                "proposal_count"
            ),
        )
        .outerjoin(observation_counts, Model.id == observation_counts.c.model_id)
        .outerjoin(
            pending_proposal_counts, Model.id == pending_proposal_counts.c.model_id
        )
    )

    # Apply filters
    if has_observations is not None:
        if has_observations:
            base_query = base_query.where(
                func.coalesce(observation_counts.c.observation_count, 0) > 0
            )
        else:
            base_query = base_query.where(
                func.coalesce(observation_counts.c.observation_count, 0) == 0
            )

    # Apply filter for pending proposals if specified
    if has_pending_proposals is not None:
        if has_pending_proposals:
            base_query = base_query.where(
                func.coalesce(pending_proposal_counts.c.proposal_count, 0) > 0
            )
        else:
            base_query = base_query.where(
                func.coalesce(pending_proposal_counts.c.proposal_count, 0) == 0
            )

    if active is not None:
        base_query = base_query.where(Model.active == active)

    # Apply experimental states filter if specified
    if experimental_states and len(experimental_states) > 0:
        # Handle the case where EXPERIMENTAL is the default (null in database)
        if "EXPERIMENTAL" in experimental_states:
            base_query = base_query.where(
                (Model.experimental_state_id == None)
                | (
                    Model.experimental_state.has(
                        ExperimentalState.name.in_(experimental_states)
                    )
                )
            )
        else:
            base_query = base_query.where(
                Model.experimental_state.has(
                    ExperimentalState.name.in_(experimental_states)
                )
            )

    # Apply permission-based filters
    if PERM.MODEL.ADMIN in current_scopes or PERM.MODEL.READ in current_scopes:
        query_results = db.execute(base_query.order_by(Model.created.desc())).all()
    else:
        query_results = db.execute(
            base_query.where(Model.creator == user).order_by(Model.created.desc())
        ).all()

    # Extract models from results and cache the counts
    models = []
    for model, note_count, proposal_count in query_results:
        # Cache the counts to avoid additional queries
        model._observational_note_count = note_count
        model._pending_proposal_count = proposal_count
        models.append(model)

    payload = {
        "data": [model.to_dict() for model in models],
        "total": len(models),
    }

    return payload


@model_router.post(
    "/api/model",
    dependencies=[Depends(am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.WRITE]))],
    response_model=ModelCreatedResponse,
)
def register_model(
    model_request: CreateModelRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    if model_request.name is None or model_request.name.strip() == "":
        name = model_request.slug
    else:
        name = model_request.name

    model = Model(
        created_by=user.id,
        slug=model_request.slug,
        name=name,
        providers=[
            Provider(
                name=provider.name,
                created_by=user.id,
                provider_class=provider.provider_class,
                config=json.dumps(provider.config),
                is_default=provider.is_default,
            )
            for provider in model_request.providers
        ],
        active=True,
        experimental_state_id=experimental_state_id_for(
            db, EXPERIMENTAL_STATE.EXPERIMENTAL
        ),
    )
    db.add(model)
    db.flush()
    db.refresh(model)
    return {
        "id": model.external_id,
    }


@model_router.patch(
    "/api/model/{external_id}",
    dependencies=[Depends(am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.WRITE]))],
    response_model=Union[ModelResponse, ModelDetailResponse],
)
def update_model(
    external_id: str,
    model_update: UpdateModelRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    include_runs: bool = Query(default=False),
    current_scopes=Depends(am.current_scopes),
):
    model = db.query(Model)
    if include_runs:
        model = model.options(selectinload(Model.runs))
    model = model.filter(Model.external_id == external_id).first()
    creator = db.scalars(select(User).where(User.id == model.creator.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with external_id {external_id} not found",
        )

    if creator != editor and PERM.MODEL.ADMIN not in current_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Model with external_id {external_id} is not editable by {editor.external_id} without the model:admin permission",
        )

    update_data = model_update.model_dump(exclude_unset=True)
    # Update each provided field

    if "active" in update_data:
        model.active = update_data["active"]

    if "name" in update_data:
        model.name = update_data["name"].strip()

    if "providers" in update_data:
        existing_provider_updates = set()
        existing_providers = {
            provider.external_id: provider for provider in model.providers
        }

        logger.info(
            "Existing providers", existing_provider_keys=existing_providers.keys()
        )

        for provider in update_data["providers"]:
            logger.info("current update provider", provider=provider)
            if not provider.get("id"):
                model.providers.append(Provider(created_by=editor.id, **provider))
            else:
                existing_provider_updates.add(provider["id"])
                op_on_provider = existing_providers[provider["id"]]

                for field, value in provider.items():
                    if field == "id":
                        continue
                    setattr(op_on_provider, field, value)

        remove_providers = [
            provider
            for provider in existing_providers.values()
            if provider.external_id not in existing_provider_updates
        ]
        for provider in remove_providers:
            db.delete(provider)

        db.add(model)
        db.flush()
        db.refresh(model)

    return model.to_dict()


@model_router.delete(
    "/api/model/{external_id}",
    dependencies=[
        Depends(am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.WRITE])),
    ],
)
def delete_model(
    external_id: str,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    current_scopes=Depends(am.current_scopes),
):
    model = db.query(Model).filter(Model.external_id == external_id).first()
    creator = db.scalars(select(User).where(User.id == model.creator.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if creator != editor and PERM.MODEL.ADMIN not in current_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if model.usage != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    db.delete(model)
    db.flush()


@model_router.get(
    "/api/model/{external_id}",
    response_model=ModelDetailResponse,
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.WRITE, PERM.MODEL.READ])
        )
    ],
)
def get_model(
    external_id: str,
    db: Session = Depends(get_managed_session),
    current_scopes=Depends(am.current_scopes),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    # Create a subquery to get observation count
    observation_count = (
        select(func.count().label("count"))
        .select_from(schema.research.model_log)
        .join(
            schema.research.log,
            schema.research.model_log.c.log_id == schema.research.log.c.id,
        )
        .join(
            schema.research.note,
            schema.research.log.c.note_id == schema.research.note.c.id,
        )
        .where(
            schema.research.model_log.c.model_id == Model.id,
            schema.research.note.c.kind_slug == "OBSERVATION",
        )
        .correlate(Model)
        .scalar_subquery()
    ).label("observation_count")

    # Create a subquery to get pending proposal count
    pending_proposal_count = (
        select(func.count().label("count"))
        .select_from(schema.research.model_experimental_state_proposal)
        .where(
            schema.research.model_experimental_state_proposal.c.model_id == Model.id,
            (
                schema.research.model_experimental_state_proposal.c.accepted.is_(None)
                | (
                    schema.research.model_experimental_state_proposal.c.accepted
                    == False
                )
            ),
            (
                schema.research.model_experimental_state_proposal.c.rejected.is_(None)
                | (
                    schema.research.model_experimental_state_proposal.c.rejected
                    == False
                )
            ),
        )
        .correlate(Model)
        .scalar_subquery()
    ).label("proposal_count")

    # Build the query with loaded relationships and the counts
    model_query = (
        select(Model, observation_count, pending_proposal_count)
        .options(selectinload(Model.runs))
        .options(selectinload(Model.logs))
        .options(selectinload(Model.proposals))
        .filter(Model.external_id == external_id)
    )

    if PERM.MODEL.ADMIN in current_scopes or PERM.MODEL.READ in current_scopes:
        result = db.execute(model_query).first()
    else:
        result = db.execute(model_query.where(Model.creator == user)).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with external_id {external_id} not found",
        )

    model, note_count, proposal_count = result
    # Cache the counts to avoid additional queries
    model._observational_note_count = note_count
    model._pending_proposal_count = proposal_count

    for provider in model.providers:
        logger.info("Provider Type", provider_type=type(provider))

    return model.to_dict(include_runs=False, include_logs=True, include_proposals=True)


@model_router.post(
    "/api/model/{external_id}/experimental-state/proposal",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [
                    PERM.MODEL.EXPERIMENT.PROPOSE,
                    PERM.MODEL.ADMIN,
                    PERM.MODEL.EXPERIMENT.APPROVE,
                ]
            )
        ),
    ],
)
def propose_model_experimental_state(
    external_id: str,
    request: ModelExperimentalStateProposalRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    model = db.query(Model).filter(Model.external_id == external_id).first()
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    actual_current_state = (
        model.experimental_state.name
        if model.experimental_state
        else EXPERIMENTAL_STATE.EXPERIMENTAL.value
    )
    if actual_current_state != request.current_state:
        logger.info(
            f"Current state mismatch. Actual: {actual_current_state}, Proposed: {request.current_state}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current state mismatch. Please reload the page and try again.",
        )

    proposed_state_id = experimental_state_id_for(
        db, EXPERIMENTAL_STATE[request.proposed_state]
    )
    if proposed_state_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Proposed state not found."
        )

    if not request.note:
        note = "Proposal Created"
    else:
        note = request.note

    log = ExperimentalStateProposal(
        user=user,
        model=model,
        note=note,
    )
    db.add(log)
    db.flush()
    db.refresh(log)

    proposal = ModelExperimentalStateProposal(
        creator=user,
        model=model,
        new_experiment_state_id=proposed_state_id,
        log=log,
    )
    db.add(proposal)
    db.flush()
    db.refresh(proposal)

    return {
        "id": proposal.id,
    }


@model_router.post(
    "/api/model/{external_id}/experimental-state/proposal/{proposal_external_id}/approve",
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.EXPERIMENT.APPROVE])
        ),
    ],
)
def approve_model_experimental_state_proposal(
    external_id: str,
    proposal_external_id: str,
    request: ModelExperimentalStateApprovalRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    proposal = (
        db.query(ModelExperimentalStateProposal)
        .join(Model)
        .filter(
            ModelExperimentalStateProposal.external_id == proposal_external_id,
            Model.external_id == external_id,
        )
        .first()
    )
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found."
        )

    for other_proposal in proposal.model.proposals:
        if (
            proposal.id == other_proposal.id
            or other_proposal.accepted
            or other_proposal.rejected
        ):
            continue

        log = ExperimentalStateRejection(
            user=user,
            model=proposal.model,
            note="Proposal rejected by other approval",
        )
        db.add(log)
        db.flush()
        db.refresh(log)
        other_proposal.reject(user, log)
        db.add(other_proposal)

    if not request.note:
        note = "Proposal Approved"
    else:
        note = request.note

    log = ExperimentalStateApproval(
        user=user,
        model=proposal.model,
        note=note,
    )

    db.add(log)
    db.flush()
    db.refresh(log)
    proposal.approve(user, log)
    proposal.model.experimental_state = proposal.new_experiment_state

    db.add(proposal)
    db.flush()
    db.refresh(proposal)
    return {
        "id": proposal.id,
    }


@model_router.get(
    "/api/model/{external_id}/experimental-state/proposal",
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.READ, PERM.MODEL.WRITE])
        ),
    ],
)
def get_model_experimental_state_proposals(
    db: Session = Depends(get_managed_session),
):
    proposals = db.query(ModelExperimentalStateProposal).all()
    return [proposal.to_dict() for proposal in proposals]


@model_router.get(
    "/api/model/{external_id}/experimental-state/proposal/{proposal_external_id}",
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.READ, PERM.MODEL.WRITE])
        ),
    ],
)
def get_model_experimental_state_proposal(
    external_id: str,
    proposal_external_id: str,
    db: Session = Depends(get_managed_session),
):
    proposal = (
        db.query(ModelExperimentalStateProposal)
        .join(Model)
        .filter(
            ModelExperimentalStateProposal.external_id == proposal_external_id,
            Model.external_id == external_id,
        )
        .first()
    )
    return proposal.to_dict()


@model_router.post(
    "/api/model/{external_id}/experimental-state/proposal/{proposal_external_id}/reject",
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.EXPERIMENT.APPROVE])
        ),
    ],
)
def reject_model_experimental_state_proposal(
    external_id: str,
    proposal_external_id: str,
    request: ModelExperimentalStateRejectionRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    proposal = (
        db.query(ModelExperimentalStateProposal)
        .join(Model)
        .filter(
            ModelExperimentalStateProposal.external_id == proposal_external_id,
            Model.external_id == external_id,
        )
        .first()
    )
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if not request.note:
        note = "Proposal Rejected"
    else:
        note = request.note

    log = ExperimentalStateRejection(
        user=user,
        model=proposal.model,
        note=note,
    )
    db.add(log)
    db.flush()
    db.refresh(log)
    proposal.reject(user, log)
    proposal.model.experimental_state = proposal.new_experiment_state
    db.add(proposal)
    db.flush()
    db.refresh(proposal)

    return {
        "id": proposal.id,
    }


@model_router.post(
    "/api/model/{external_id}/observe",
    dependencies=[
        Depends(am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.REVIEW])),
    ],
)
def observe_model(
    external_id: str,
    request: ModelObservationRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    model = db.query(Model).filter(Model.external_id == external_id).first()
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model not found."
        )

    if not request.note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Note is required."
        )

    log = ModelObservation(
        user=user,
        model=model,
        note=request.note,
    )

    db.add(log)
    db.flush()
    db.refresh(log)

    return model.to_dict(include_runs=False, include_logs=True, include_proposals=True)


@model_router.get(
    "/api/model/metadata/experimental-state",
    dependencies=[
        Depends(
            am.require_any_scopes([PERM.MODEL.ADMIN, PERM.MODEL.READ, PERM.MODEL.WRITE])
        ),
    ],
    response_model=ListResponse[ExperimentalStateResponse],
)
def get_model_experimental_states(
    db: Session = Depends(get_managed_session),
):
    VALID_STATES = [
        EXPERIMENTAL_STATE.EXPERIMENTAL.value,
        EXPERIMENTAL_STATE.RELEASED.value,
        EXPERIMENTAL_STATE.DEPRECATED.value,
        EXPERIMENTAL_STATE.REJECTED.value,
    ]

    states = (
        db.query(ExperimentalState)
        .filter(ExperimentalState.name.in_(VALID_STATES))
        .all()
    )
    return {
        "data": [state.to_dict() for state in states],
        "total": len(states),
    }
