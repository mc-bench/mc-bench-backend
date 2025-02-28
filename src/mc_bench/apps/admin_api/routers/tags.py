from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.apps.admin_api.config import settings
from mc_bench.apps.admin_api.transport_types.generic import ListResponse
from mc_bench.apps.admin_api.transport_types.responses import (
    TagResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.prompt import Tag
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

tag_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


@tag_router.get(
    "/api/tag",
    dependencies=[
        Depends(
            am.require_any_scopes(
                [PERM.PROMPT.ADMIN, PERM.PROMPT.READ, PERM.PROMPT.WRITE]
            )
        ),
    ],
    response_model=ListResponse[TagResponse],
)
def get_tags(
    db: Session = Depends(get_managed_session),
):
    tags = list(db.scalars(select(Tag).order_by(Tag.created.desc())))
    payload = {
        "data": [tag.to_dict() for tag in tags],
        "total": len(tags),
    }

    return payload
