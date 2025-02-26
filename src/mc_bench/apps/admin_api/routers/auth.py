from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.responses import (
    RoleResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.user import Role
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

auth_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@auth_router.get(
    "/api/auth/role",
    dependencies=[
        Depends(am.require_any_scopes([PERM.USER.ADMIN])),
    ],
    response_model=ListResponse[RoleResponse],
)
def get_roles(
    db: Session = Depends(get_managed_session),
):
    roles = list(db.scalars(select(Role)))
    payload = {
        "data": [role.to_dict() for role in roles],
        "total": len(roles),
    }

    return payload
