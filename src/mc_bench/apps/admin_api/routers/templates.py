from typing import List, Optional, Union

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import mc_bench.schema.postgres as schema
from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import (
    CreateTemplateRequest,
    TemplateExperimentalStateApprovalRequest,
    TemplateExperimentalStateProposalRequest,
    TemplateExperimentalStateRejectionRequest,
    TemplateObservationRequest,
    UpdateTemplateRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    ExperimentalStateResponse,
    TemplateCreatedResponse,
    TemplateDetailResponse,
    TemplateResponse,
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
    TemplateObservation,
)
from mc_bench.models.template import Template, TemplateExperimentalStateProposal
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session

logger = get_logger(__name__)

template_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@template_router.get(
    "/api/template",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.READ, PERM.TEMPLATE.WRITE]
            )
        ),
    ],
    response_model=ListResponse[TemplateResponse],
)
def get_templates(
    db: Session = Depends(get_managed_session),
    current_scopes: List[str] = Depends(am.current_scopes),
    user_uuid: str = Depends(am.get_current_user_uuid),
    has_observations: Optional[bool] = None,
    has_pending_proposals: Optional[bool] = None,
    active: Optional[bool] = None,
    experimental_states: Optional[List[str]] = Query(None),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    # Create a subquery to get observation counts in bulk
    observation_counts = (
        select(
            schema.research.template_log.c.template_id.label("template_id"),
            func.count().label("observation_count"),
        )
        .select_from(schema.research.template_log)
        .join(
            schema.research.log,
            schema.research.template_log.c.log_id == schema.research.log.c.id,
        )
        .join(
            schema.research.note,
            schema.research.log.c.note_id == schema.research.note.c.id,
        )
        .where(schema.research.note.c.kind_slug == "OBSERVATION")
        .group_by(schema.research.template_log.c.template_id)
        .subquery()
    )

    # Create a subquery to get pending proposal counts in bulk
    pending_proposal_counts = (
        select(
            schema.research.template_experimental_state_proposal.c.template_id.label(
                "template_id"
            ),
            func.count().label("proposal_count"),
        )
        .select_from(schema.research.template_experimental_state_proposal)
        .where(
            (
                schema.research.template_experimental_state_proposal.c.accepted.is_(
                    None
                )
                | (
                    schema.research.template_experimental_state_proposal.c.accepted
                    == False
                )
            ),
            (
                schema.research.template_experimental_state_proposal.c.rejected.is_(
                    None
                )
                | (
                    schema.research.template_experimental_state_proposal.c.rejected
                    == False
                )
            ),
        )
        .group_by(schema.research.template_experimental_state_proposal.c.template_id)
        .subquery()
    )

    # Build the base query with the left joins to include templates with zero counts
    base_query = (
        select(
            Template,
            func.coalesce(observation_counts.c.observation_count, 0).label(
                "note_count"
            ),
            func.coalesce(pending_proposal_counts.c.proposal_count, 0).label(
                "proposal_count"
            ),
        )
        .outerjoin(observation_counts, Template.id == observation_counts.c.template_id)
        .outerjoin(
            pending_proposal_counts,
            Template.id == pending_proposal_counts.c.template_id,
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
        base_query = base_query.where(Template.active == active)

    # Apply experimental states filter if specified
    if experimental_states and len(experimental_states) > 0:
        # Handle the case where EXPERIMENTAL is the default (null in database)
        if "EXPERIMENTAL" in experimental_states:
            base_query = base_query.where(
                (Template.experimental_state_id == None)
                | (
                    Template.experimental_state.has(
                        ExperimentalState.name.in_(experimental_states)
                    )
                )
            )
        else:
            base_query = base_query.where(
                Template.experimental_state.has(
                    ExperimentalState.name.in_(experimental_states)
                )
            )

    # Apply permission-based filters
    if PERM.TEMPLATE.ADMIN in current_scopes or PERM.TEMPLATE.READ in current_scopes:
        query_results = db.execute(base_query.order_by(Template.created.desc())).all()
    else:
        query_results = db.execute(
            base_query.where(Template.author == user).order_by(Template.created.desc())
        ).all()

    # Extract templates from results and cache the counts
    templates = []
    for template, note_count, proposal_count in query_results:
        # Cache the counts to avoid additional queries
        template._observational_note_count = note_count
        template._pending_proposal_count = proposal_count
        templates.append(template)

    payload = {
        "data": [template.to_dict() for template in templates],
        "total": len(templates),
    }

    return payload


@template_router.post(
    "/api/template",
    dependencies=[
        Depends(am.require_any_scopes([PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.WRITE]))
    ],
    response_model=TemplateCreatedResponse,
)
def create_template(
    template: CreateTemplateRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    template = Template(
        author=user,
        name=template.name,
        description=template.description,
        content=template.content,
        active=True,
        minecraft_version="1.21.1",
        experimental_state_id=experimental_state_id_for(
            db, EXPERIMENTAL_STATE.EXPERIMENTAL
        ),
    )
    db.add(template)
    db.flush()
    db.refresh(template)
    return {
        "id": template.external_id,
    }


@template_router.patch(
    "/api/template/{external_id}",
    dependencies=[
        Depends(am.require_any_scopes([PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.WRITE]))
    ],
    response_model=Union[TemplateResponse, TemplateDetailResponse],
)
def update_template(
    external_id: str,
    template_update: UpdateTemplateRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    include_runs: bool = Query(default=False),
    current_scopes: List[str] = Depends(am.current_scopes),
):
    template = db.query(Template)
    if include_runs:
        template = template.options(selectinload(Template.runs))

    template = template.filter(Template.external_id == external_id).first()
    author = db.scalars(select(User).where(User.id == template.author.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    # TODO: Implement logic that ensures we don't edit the content of a template that has usages
    # TODO: Add validation that we have implemented the required template variables e.e. {{ build_description }}

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with external_id {external_id} not found",
        )

    if author != editor and PERM.TEMPLATE.ADMIN not in current_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Template with external_id {external_id} is not editable by {editor.external_id} without the template:admin permission",
        )

    update_data = template_update.model_dump(exclude_unset=True)

    # Update each provided field
    for field, value in update_data.items():
        setattr(template, field, value)

    db.add(template)

    db.flush()
    db.refresh(template)

    return template.to_dict(
        include_runs=include_runs,
    )


@template_router.delete(
    "/api/template/{external_id}",
    dependencies=[
        Depends(am.require_any_scopes([PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.WRITE])),
    ],
)
def delete_template(
    external_id: str,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    current_scopes=Depends(am.current_scopes),
):
    template = db.query(Template).filter(Template.external_id == external_id).first()
    author = db.scalars(select(User).where(User.id == template.author.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if author != editor and PERM.TEMPLATE.ADMIN not in current_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if template.usage != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    db.delete(template)


@template_router.get(
    "/api/template/{external_id}",
    response_model=TemplateDetailResponse,
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.WRITE, PERM.TEMPLATE.READ]
            )
        )
    ],
)
def get_template(
    external_id: str,
    db: Session = Depends(get_managed_session),
    current_scopes: List[str] = Depends(am.current_scopes),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    # Create a subquery to get observation count
    observation_count = (
        select(func.count().label("count"))
        .select_from(schema.research.template_log)
        .join(
            schema.research.log,
            schema.research.template_log.c.log_id == schema.research.log.c.id,
        )
        .join(
            schema.research.note,
            schema.research.log.c.note_id == schema.research.note.c.id,
        )
        .where(
            schema.research.template_log.c.template_id == Template.id,
            schema.research.note.c.kind_slug == "OBSERVATION",
        )
        .correlate(Template)
        .scalar_subquery()
    ).label("observation_count")

    # Create a subquery to get pending proposal count
    pending_proposal_count = (
        select(func.count().label("count"))
        .select_from(schema.research.template_experimental_state_proposal)
        .where(
            schema.research.template_experimental_state_proposal.c.template_id
            == Template.id,
            (
                schema.research.template_experimental_state_proposal.c.accepted.is_(
                    None
                )
                | (
                    schema.research.template_experimental_state_proposal.c.accepted
                    == False
                )
            ),
            (
                schema.research.template_experimental_state_proposal.c.rejected.is_(
                    None
                )
                | (
                    schema.research.template_experimental_state_proposal.c.rejected
                    == False
                )
            ),
        )
        .correlate(Template)
        .scalar_subquery()
    ).label("proposal_count")

    # Build the query with loaded relationships and the counts
    template_query = (
        select(Template, observation_count, pending_proposal_count)
        .options(selectinload(Template.runs))
        .options(selectinload(Template.logs))
        .options(selectinload(Template.proposals))
        .filter(Template.external_id == external_id)
    )

    if PERM.TEMPLATE.ADMIN in current_scopes or PERM.TEMPLATE.READ in current_scopes:
        result = db.execute(template_query).first()
    else:
        result = db.execute(template_query.where(Template.author == user)).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with external_id {external_id} not found",
        )

    template, note_count, proposal_count = result
    # Cache the counts to avoid additional queries
    template._observational_note_count = note_count
    template._pending_proposal_count = proposal_count

    return template.to_dict(
        include_runs=False, include_logs=True, include_proposals=True
    )


@template_router.post(
    "/api/template/{external_id}/experimental-state/proposal",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [
                    PERM.TEMPLATE.EXPERIMENT.PROPOSE,
                    PERM.TEMPLATE.ADMIN,
                    PERM.TEMPLATE.EXPERIMENT.APPROVE,
                ]
            )
        ),
    ],
)
def propose_template_experimental_state(
    external_id: str,
    request: TemplateExperimentalStateProposalRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    template = db.query(Template).filter(Template.external_id == external_id).first()
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    actual_current_state = (
        template.experimental_state.name
        if template.experimental_state
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
        template=template,
        note=note,
    )
    db.add(log)
    db.flush()
    db.refresh(log)

    proposal = TemplateExperimentalStateProposal(
        creator=user,
        template=template,
        new_experiment_state_id=proposed_state_id,
        log=log,
    )
    db.add(proposal)
    db.flush()
    db.refresh(proposal)

    return {
        "id": proposal.id,
    }


@template_router.post(
    "/api/template/{external_id}/experimental-state/proposal/{proposal_external_id}/approve",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.EXPERIMENT.APPROVE]
            )
        ),
    ],
)
def approve_template_experimental_state_proposal(
    external_id: str,
    proposal_external_id: str,
    request: TemplateExperimentalStateApprovalRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    proposal = (
        db.query(TemplateExperimentalStateProposal)
        .join(Template)
        .filter(
            TemplateExperimentalStateProposal.external_id == proposal_external_id,
            Template.external_id == external_id,
        )
        .first()
    )
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found."
        )

    for other_proposal in proposal.template.proposals:
        if (
            proposal.id == other_proposal.id
            or other_proposal.accepted
            or other_proposal.rejected
        ):
            continue

        log = ExperimentalStateRejection(
            user=user,
            template=proposal.template,
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
        template=proposal.template,
        note=note,
    )

    db.add(log)
    db.flush()
    db.refresh(log)
    proposal.approve(user, log)
    proposal.template.experimental_state = proposal.new_experiment_state

    db.add(proposal)
    db.flush()
    db.refresh(proposal)
    return {
        "id": proposal.id,
    }


@template_router.get(
    "/api/template/{external_id}/experimental-state/proposal",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.READ, PERM.TEMPLATE.WRITE]
            )
        ),
    ],
)
def get_template_experimental_state_proposals(
    db: Session = Depends(get_managed_session),
):
    proposals = db.query(TemplateExperimentalStateProposal).all()
    return [proposal.to_dict() for proposal in proposals]


@template_router.get(
    "/api/template/{external_id}/experimental-state/proposal/{proposal_external_id}",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.READ, PERM.TEMPLATE.WRITE]
            )
        ),
    ],
)
def get_template_experimental_state_proposal(
    external_id: str,
    proposal_external_id: str,
    db: Session = Depends(get_managed_session),
):
    proposal = (
        db.query(TemplateExperimentalStateProposal)
        .join(Template)
        .filter(
            TemplateExperimentalStateProposal.external_id == proposal_external_id,
            Template.external_id == external_id,
        )
        .first()
    )
    return proposal.to_dict()


@template_router.post(
    "/api/template/{external_id}/experimental-state/proposal/{proposal_external_id}/reject",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.EXPERIMENT.APPROVE]
            )
        ),
    ],
)
def reject_template_experimental_state_proposal(
    external_id: str,
    proposal_external_id: str,
    request: TemplateExperimentalStateRejectionRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    proposal = (
        db.query(TemplateExperimentalStateProposal)
        .join(Template)
        .filter(
            TemplateExperimentalStateProposal.external_id == proposal_external_id,
            Template.external_id == external_id,
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
        template=proposal.template,
        note=note,
    )
    db.add(log)
    db.flush()
    db.refresh(log)
    proposal.reject(user, log)
    proposal.template.experimental_state = proposal.new_experiment_state
    db.add(proposal)
    db.flush()
    db.refresh(proposal)

    return {
        "id": proposal.id,
    }


@template_router.post(
    "/api/template/{external_id}/observe",
    dependencies=[
        Depends(am.require_any_scopes([PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.REVIEW])),
    ],
)
def observe_template(
    external_id: str,
    request: TemplateObservationRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    template = db.query(Template).filter(Template.external_id == external_id).first()
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found."
        )

    if not request.note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Note is required."
        )

    log = TemplateObservation(
        user=user,
        template=template,
        note=request.note,
    )

    db.add(log)
    db.flush()
    db.refresh(log)

    return template.to_dict(
        include_runs=False, include_logs=True, include_proposals=True
    )


@template_router.get(
    "/api/template/metadata/experimental-state",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.TEMPLATE.ADMIN, PERM.TEMPLATE.READ, PERM.TEMPLATE.WRITE]
            )
        ),
    ],
    response_model=ListResponse[ExperimentalStateResponse],
)
def get_template_experimental_states(
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
