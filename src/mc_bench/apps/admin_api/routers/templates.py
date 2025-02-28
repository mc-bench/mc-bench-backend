from typing import List, Union

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if PERM.TEMPLATE.ADMIN in current_scopes or PERM.TEMPLATE.READ in current_scopes:
        templates = list(db.scalars(select(Template).order_by(Template.created.desc())))
    else:
        templates = list(
            db.scalars(
                select(Template)
                .where(Template.author == user)
                .order_by(Template.created.desc())
            )
        )

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

    template = (
        db.query(Template)
        .options(selectinload(Template.runs))
        .filter(Template.external_id == external_id)
    )

    if PERM.TEMPLATE.ADMIN in current_scopes or PERM.TEMPLATE.READ in current_scopes:
        template = template.first()
    else:
        template = template.where(Template.author == user).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with external_id {external_id} not found",
        )

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
