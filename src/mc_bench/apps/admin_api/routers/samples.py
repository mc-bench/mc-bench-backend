from typing import List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from mc_bench.auth.permissions import PERM
from mc_bench.models.log import SampleApproval, SampleObservation, SampleRejection
from mc_bench.models.model import Model
from mc_bench.models.prompt import Prompt
from mc_bench.models.run import Run, Sample, SampleApprovalState
from mc_bench.models.template import Template
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

from ..config import settings
from ..transport_types.requests import SampleActionRequest
from ..transport_types.requests import SampleApprovalState as SampleApprovalStateEnum
from ..transport_types.responses import (
    PagedListResponse,
    SampleDetailResponse,
    SampleResponse,
)

sample_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@sample_router.get(
    "/api/sample",
    dependencies=[
        Depends(am.require_any_scopes([PERM.SAMPLE.ADMIN, PERM.SAMPLE.READ])),
    ],
    response_model=PagedListResponse[SampleResponse],
)
def list_samples(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    model_id: Optional[List[UUID]] = Query(None),
    template_id: Optional[List[UUID]] = Query(None),
    prompt_id: Optional[List[UUID]] = Query(None),
    run_id: Optional[List[UUID]] = Query(None),
    approval_state: Optional[List[SampleApprovalStateEnum]] = Query(None),
    pending: Optional[bool] = Query(None),
    complete: Optional[bool] = Query(None),
    db: Session = Depends(get_managed_session),
):
    # Build base query with needed joins
    query = (
        select(Sample)
        .join(Sample.run)
        .options(
            selectinload(Sample.run).joinedload(Run.model),
            selectinload(Sample.run).joinedload(Run.prompt),
            selectinload(Sample.run).joinedload(Run.template),
        )
    )

    # Apply filters
    if model_id:
        query = query.join(Run.model).filter(Model.external_id.in_(model_id))

    if template_id:
        query = query.join(Run.template).filter(Template.external_id.in_(template_id))

    if prompt_id:
        query = query.join(Run.prompt).filter(Prompt.external_id.in_(prompt_id))

    if run_id:
        query = query.filter(Sample.run_id.in_(run_id))

    if approval_state:
        print(f"approval_state: {approval_state}")
        valid_approval_filters = [
            state.value
            for state in approval_state
            if state
            in [
                SampleApprovalStateEnum.APPROVED,
                SampleApprovalStateEnum.REJECTED,
            ]
        ]

        pending_approval_filter = Sample.approval_state_id.is_(None)

        if (
            valid_approval_filters
            and SampleApprovalStateEnum.PENDING_APPROVAL not in approval_state
        ):
            approval_filter = SampleApprovalState.name.in_(valid_approval_filters)
            query = query.outerjoin(Sample.approval_state).filter(approval_filter)
        elif (
            SampleApprovalStateEnum.PENDING_APPROVAL in approval_state
            and len(approval_state) == 1
        ):
            approval_filter = pending_approval_filter
            query = query.filter(approval_filter)
        else:
            approval_filter = or_(
                SampleApprovalState.name.in_(valid_approval_filters),
                pending_approval_filter,
            )
            query = query.outerjoin(Sample.approval_state).filter(approval_filter)

    if pending is not None:
        if pending:
            query = query.filter(Sample.is_pending == True)  # noqa: E712
        else:
            query = query.filter(Sample.is_pending == False)  # noqa: E712

    if complete is not None:
        if complete:
            query = query.filter(Sample.is_complete == True)  # noqa: E712
        else:
            query = query.filter(Sample.is_complete == False)  # noqa: E712

    # Always sort by created descending
    query = query.order_by(Sample.created.desc())
    print(f"query: {query.compile(compile_kwargs={'literal_binds': True})}")

    # Execute query and handle pagination
    total = db.scalar(select(func.count()).select_from(query.subquery()))

    query = query.offset((page - 1) * page_size).limit(page_size)
    samples = db.scalars(query).all()

    return {
        "data": [sample.to_dict(include_run=True) for sample in samples],
        "paging": {
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "totalItems": total,
            "hasNext": page * page_size < total,
            "hasPrevious": page > 1,
        },
    }


@sample_router.get(
    "/api/sample/{external_id}",
    dependencies=[
        Depends(am.require_any_scopes([PERM.SAMPLE.ADMIN, PERM.SAMPLE.READ])),
    ],
    response_model=SampleDetailResponse,
)
def get_sample(
    external_id: str,
    db: Session = Depends(get_managed_session),
):
    sample = db.scalar(select(Sample).where(Sample.external_id == external_id))
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample with external_id {external_id} not found",
        )
    return sample.to_dict(
        include_run_detail=True, include_logs=True, include_artifacts=True
    )


@sample_router.post(
    "/api/sample/{external_id}/approve",
    dependencies=[
        Depends(am.require_any_scopes([PERM.VOTING.ADMIN])),
    ],
    response_model=SampleResponse,
)
def approve_sample(
    external_id: str,
    request: SampleActionRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    sample = db.scalar(select(Sample).where(Sample.external_id == external_id))
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample with external_id {external_id} not found",
        )

    user = db.scalar(select(User).where(User.external_id == user_uuid))

    approved_state = db.scalar(
        select(SampleApprovalState).where(SampleApprovalState.name == "APPROVED")
    )
    sample.approval_state = approved_state
    sample_approval = SampleApproval(
        sample=sample,
        user=user,
        note=request.note,
    )
    db.add(sample_approval)
    db.add(sample)
    db.commit()
    return sample.to_dict(
        include_run_detail=True, include_logs=True, include_artifacts=True
    )


@sample_router.post(
    "/api/sample/{external_id}/reject",
    dependencies=[
        Depends(am.require_any_scopes([PERM.VOTING.ADMIN])),
    ],
    response_model=SampleResponse,
)
def reject_sample(
    external_id: str,
    request: SampleActionRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    sample = db.scalar(select(Sample).where(Sample.external_id == external_id))
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample with external_id {external_id} not found",
        )

    user = db.scalar(select(User).where(User.external_id == user_uuid))
    rejected_state = db.scalar(
        select(SampleApprovalState).where(SampleApprovalState.name == "REJECTED")
    )
    sample.approval_state = rejected_state
    sample_rejection = SampleRejection(
        sample=sample,
        user=user,
        note=request.note,
    )
    db.add(sample_rejection)
    db.add(sample)
    db.commit()
    return sample.to_dict(
        include_run_detail=True, include_logs=True, include_artifacts=True
    )


@sample_router.post(
    "/api/sample/{external_id}/observe",
    dependencies=[
        Depends(am.require_any_scopes([PERM.SAMPLE.ADMIN, PERM.SAMPLE.REVIEW])),
    ],
    response_model=SampleResponse,
)
def observe_sample(
    external_id: str,
    request: SampleActionRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    sample = db.scalar(select(Sample).where(Sample.external_id == external_id))
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample with external_id {external_id} not found",
        )

    user = db.scalar(select(User).where(User.external_id == user_uuid))

    sample_observation = SampleObservation(
        sample=sample,
        user=user,
        note=request.note,
    )
    db.add(sample_observation)
    db.commit()
    return sample.to_dict(
        include_run_detail=True, include_logs=True, include_artifacts=True
    )
