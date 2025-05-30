from fastapi import Depends, Query
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.requests import UpdateRolesRequest
from mc_bench.apps.admin_api.transport_types.responses import (
    UserResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.user import Role, User, UserRole
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session

user_router = APIRouter()

logger = get_logger(__name__)

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@user_router.get(
    "/api/user/search",
    dependencies=[
        Depends(am.require_any_scopes([PERM.USER.ADMIN])),
    ],
    response_model=ListResponse[UserResponse],
)
def search_users(
    username: str = Query(None, description="The username to search for"),
    db: Session = Depends(get_managed_session),
    limit: int = Query(100, description="The maximum number of users to return"),
):
    logger.info("Searching for users", username=username, limit=limit)
    users = list(
        db.scalars(
            select(User)
            .options(selectinload(User.roles).options(selectinload(Role.permissions)))
            .filter(User.username_normalized.startswith(username.lower()))
            .limit(limit)
        )
    )
    payload = {
        "data": [user.to_dict() for user in users],
        "total": len(users),
    }

    return payload


@user_router.get(
    "/api/user/{user_id}",
    dependencies=[
        Depends(am.require_any_scopes([PERM.USER.ADMIN])),
    ],
    response_model=UserResponse,
)
def get_user(user_id: str, db: Session = Depends(get_managed_session)):
    user = db.scalar(select(User).where(User.external_id == user_id))
    return user.to_dict()


@user_router.put(
    "/api/user/{user_id}/role",
    dependencies=[
        Depends(am.require_any_scopes([PERM.USER.ADMIN])),
    ],
    response_model=UserResponse,
)
def update_roles(
    user_id: str,
    request: UpdateRolesRequest,
    db: Session = Depends(get_managed_session),
    user_uuid: str = Depends(am.get_current_user_uuid),
):
    admin_user = db.scalar(select(User).where(User.external_id == user_uuid))
    user = db.scalar(select(User).where(User.external_id == user_id))

    current_roles = [role.external_id for role in user.roles]
    desired_roles = request.roles

    roles_to_add = [role for role in desired_roles if role not in current_roles]
    roles_to_remove = [role for role in current_roles if role not in desired_roles]

    add_role_models = db.scalars(select(Role).where(Role.external_id.in_(roles_to_add)))
    remove_role_models = db.scalars(
        select(Role).where(Role.external_id.in_(roles_to_remove))
    )

    for role in remove_role_models:
        user.roles.remove(role)

    for role in add_role_models:
        db.add(
            UserRole(
                creator=admin_user,
                user=user,
                role=role,
            )
        )

    db.add(user)
    db.flush()

    return user.to_dict()
