from typing import Union

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import (
    AddPromptTagRequest,
    CreatePromptRequest,
    DeletePromptTagRequest,
    UpdatePromptRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    PromptCreatedResponse,
    PromptDetailResponse,
    PromptResponse,
    TagListChangeResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.prompt import Prompt, Tag
from mc_bench.models.user import User
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session

logger = get_logger(__name__)

prompt_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@prompt_router.get(
    "/api/prompt",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.PROMPT.ADMIN, PERM.PROMPT.READ, PERM.PROMPT.WRITE]
            )
        ),
    ],
    response_model=ListResponse[PromptResponse],
)
def get_prompts(
    db: Session = Depends(get_managed_session),
):
    prompts = list(db.scalars(select(Prompt)))
    payload = {
        "data": [prompt.to_dict(include_runs=False) for prompt in prompts],
        "total": len(prompts),
    }

    return payload


@prompt_router.post(
    "/api/prompt",
    dependencies=[
        Depends(am.require_any_scopes([PERM.PROMPT.ADMIN, PERM.PROMPT.WRITE]))
    ],
    response_model=PromptCreatedResponse,
)
def create_prompt(
    prompt: CreatePromptRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    logger.info(f"Creating prompt with tags: {prompt.tags}")

    tags = db.scalars(select(Tag).where(Tag.name.in_(prompt.tags))).all()

    existing_tag_names = set([tag.name for tag in tags])

    new_tag_names = [
        tag_name for tag_name in prompt.tags if tag_name not in existing_tag_names
    ]

    new_tags = [Tag(name=tag_name, creator=user) for tag_name in new_tag_names]

    db.add_all(new_tags)
    db.flush()

    prompt = Prompt(
        author=user,
        name=prompt.name,
        build_specification=prompt.build_specification,
        active=True,
    )
    db.add(prompt)
    db.flush()
    db.refresh(prompt)

    for tag in tags + new_tags:
        prompt.add_tag(tag, user)

    db.flush()

    return {
        "id": prompt.external_id,
    }


@prompt_router.patch(
    "/api/prompt/{external_id}",
    dependencies=[
        Depends(am.require_any_scopes([PERM.PROMPT.ADMIN, PERM.PROMPT.WRITE]))
    ],
    response_model=Union[PromptResponse, PromptDetailResponse],
)
def update_prompt(
    external_id: str,
    prompt_update: UpdatePromptRequest,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    include_runs: bool = Query(default=False),
    current_scopes=Depends(am.current_scopes),
):
    prompt = db.query(Prompt)

    if include_runs:
        prompt = prompt.options(
            selectinload(Prompt.runs),
        )
    prompt = prompt.filter(Prompt.external_id == external_id).first()
    author = db.scalars(select(User).where(User.id == prompt.author.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()

    # TODO: Implement logic that ensures we don't edit the content of a prompt that has usages

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with external_id {external_id} not found",
        )

    if author != editor and PERM.PROMPT.ADMIN not in current_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Prompt with external_id {external_id} is not editable by {editor.external_id} without the prompt:admin permission",
        )

    update_data = prompt_update.model_dump(exclude_unset=True)
    # Update each provided field
    for field, value in update_data.items():
        setattr(prompt, field, value)

    db.add(prompt)
    db.flush()
    db.refresh(prompt)

    return prompt.to_dict(include_runs=include_runs)


@prompt_router.delete(
    "/api/prompt/{external_id}",
    dependencies=[
        Depends(am.require_any_scopes([PERM.PROMPT.ADMIN, PERM.PROMPT.WRITE])),
    ],
)
def delete_prompt(
    external_id: str,
    user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    current_scopes=Depends(am.current_scopes),
):
    prompt = db.query(Prompt).filter(Prompt.external_id == external_id).first()
    author = db.scalars(select(User).where(User.id == prompt.author.id)).one()
    editor = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    if author != editor and PERM.PROMPT.ADMIN not in current_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if prompt.usage != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    db.delete(prompt)


@prompt_router.get(
    "/api/prompt/{external_id}",
    response_model=PromptDetailResponse,
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.PROMPT.ADMIN, PERM.PROMPT.WRITE, PERM.PROMPT.READ]
            )
        )
    ],
)
def get_prompt(
    external_id: str,
    db: Session = Depends(get_managed_session),
):
    prompt = (
        db.query(Prompt)
        .options(selectinload(Prompt.runs))
        .filter(Prompt.external_id == external_id)
        .first()
    )
    return prompt.to_dict(include_runs=True)


@prompt_router.delete(
    "/api/prompt/{external_id}/tag",
    dependencies=[
        Depends(am.require_any_scopes([PERM.PROMPT.ADMIN, PERM.PROMPT.WRITE])),
    ],
    response_model=TagListChangeResponse,
)
def delete_prompt_tag(
    external_id: str,
    tag_request: DeletePromptTagRequest,
    db: Session = Depends(get_managed_session),
):
    prompt = db.query(Prompt).filter(Prompt.external_id == external_id).first()
    if tag_request.tag_name not in [tag.name for tag in prompt.tags]:
        return

    tag_to_remove = next(tag for tag in prompt.tags if tag.name == tag_request.tag_name)
    prompt.remove_tag(tag_to_remove)
    db.add(prompt)

    db.flush()
    db.refresh(prompt)

    return {
        "current_tags": [tag.to_dict() for tag in prompt.tags],
    }


@prompt_router.post(
    "/api/prompt/{external_id}/tag",
    dependencies=[
        Depends(am.require_any_scopes([PERM.PROMPT.ADMIN, PERM.PROMPT.WRITE])),
    ],
    response_model=TagListChangeResponse,
)
def add_prompt_tag(
    external_id: str,
    tag_request: AddPromptTagRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    user = db.scalars(select(User).where(User.external_id == user_uuid)).one()
    prompt = db.query(Prompt).filter(Prompt.external_id == external_id).first()

    if tag_request.tag_name in [tag.name for tag in prompt.tags]:
        return

    tag = db.query(Tag).filter(Tag.name == tag_request.tag_name).one_or_none()

    if not tag:
        tag = Tag(name=tag_request.tag_name, creator=user)
        db.add(tag)
        db.flush()

    prompt.add_tag(tag, user)

    db.add(prompt)
    db.flush()
    db.refresh(prompt)

    return {
        "current_tags": [tag.to_dict() for tag in prompt.tags],
    }
