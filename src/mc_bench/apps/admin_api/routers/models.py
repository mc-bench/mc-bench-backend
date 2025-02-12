import json
from typing import List, Union

from fastapi import Depends, HTTPException, Query, status
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import (
    CreateModelRequest,
    UpdateModelRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    ModelCreatedResponse,
    ModelDetailResponse,
    ModelResponse,
    ProviderClassResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.model import Model, ProviderClass
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
):
    models = list(db.scalars(select(Model)).all())
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
    model = Model(
        created_by=user.id,
        slug=model_request.slug,
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

    # TODO: Implement logic that ensures we don't edit the content of a model that has usages

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
):
    model = (
        db.query(Model)
        .options(selectinload(Model.runs))
        .filter(Model.external_id == external_id)
        .first()
    )

    for provider in model.providers:
        logger.info("Provider Type", provider_type=type(provider))

    return model.to_dict(include_runs=True)
