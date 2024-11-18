from sqlalchemy import select
from mc_bench.util.postgres import get_managed_session
from sqlalchemy.orm import Session
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from mc_bench.server.auth import AuthManager
import uuid
from mc_bench.models.template import Template
from pydantic import BaseModel, ConfigDict
from mc_bench.models.user import User
import humps
from typing import Generic, TypeVar, List
import datetime
from ..config import settings

template_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)

T = TypeVar("T")


class Base(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # Enables ORM model parsing
        alias_generator=humps.camelize,  # Converts snake_case to camelCase
        populate_by_name=True,  # Allows accessing fields by snake_case name
    )


class ListResponse(Base, Generic[T]):
    data: List[T]
    total: int


class TemplateResponse(Base):
    id: uuid.UUID
    created: datetime.datetime
    created_by: str
    last_modified: Optional[datetime.datetime]
    last_modified_by: Optional[str]
    name: str
    description: str
    content: str
    active: Optional[bool]
    frozen: Optional[bool]
    usage: int


class CreateTemplateRequest(BaseModel):
    name: str
    description: str
    active: bool
    content: str


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    content: Optional[str] = None


@am.require_any_scopes(["template:admin", "template:read", "template:write"])
@template_router.get("/api/template", response_model=ListResponse[TemplateResponse])
def get_templates(
    db: Session = Depends(get_managed_session),
):
    templates = list(db.scalars(select(Template)))
    payload = {
        "data": [template.to_dict() for template in templates],
        "total": len(templates),
    }

    return payload


@am.require_any_scopes(["template:admin", "template:write"])
@template_router.post("/api/template")
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


@am.require_any_scopes(["template:admin", "template:write"])
@template_router.patch("/api/template/{external_id}")
def update_template(
    external_id: str,
    template_update: UpdateTemplateRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    template = db.query(Template).filter(Template.external_id == external_id).first()
    author = db.scalars(select(User).where(User.id == template.author.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    # TODO: Implement logic that ensures we don't edit the content of a template that has usages
    # TODO: Add validation that we have implemented the required template variables e.e. {{ build_description }}

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with external_id {external_id} not found",
        )

    if author != editor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Template with external_id {external_id} is not editable by {editor.external_id} without the template:admin permission",
        )

    update_data = template_update.model_dump(exclude_unset=True)
    # Update each provided field
    for field, value in update_data.items():
        setattr(template, field, value)

    db.flush()
    db.refresh(template)

    return template.to_dict()


@am.require_any_scopes(["template:admin", "template:write"])
@template_router.delete("/api/template/{external_id}")
def delete_template(
    external_id: str,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    current_scopes=Depends(am.current_scopes),
):
    template = db.query(Template).filter(Template.external_id == external_id).first()
    author = db.scalars(select(User).where(User.id == template.author.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if author != editor and "template:admin" not in current_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if template.usage != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    db.delete(template)


@am.require_any_scopes(["template:admin", "template:write", "template:read"])
@template_router.get("/api/template/{external_id}", response_model=TemplateResponse)
def get_template(
    external_id: str,
    db: Session = Depends(get_managed_session),
):
    template = db.query(Template).filter(Template.external_id == external_id).first()
    return template.to_dict()
