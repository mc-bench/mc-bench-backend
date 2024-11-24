from typing import List, Union

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import (
    CreateTemplateRequest,
    UpdateTemplateRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    TemplateCreatedResponse,
    TemplateDetailResponse,
    TemplateResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.template import Template
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

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
):
    templates = list(db.scalars(select(Template)))
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
):
    template = (
        db.query(Template)
        .options(selectinload(Template.runs))
        .filter(Template.external_id == external_id)
        .first()
    )
    return template.to_dict(include_runs=True)
