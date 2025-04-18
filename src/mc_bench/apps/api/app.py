import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from mc_bench.apps.api.routers.comparison import comparison_router
from mc_bench.apps.api.routers.user import user_router
from mc_bench.util.logging import configure_logging

from .config import settings
from .lifespan import lifespan

configure_logging(humanize=settings.HUMANIZE_LOGS, level=settings.LOG_LEVEL)

allow_origins = os.environ.get("CORS_ALLOWED_ORIGIN", "").split(",")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-MCBench-Session", "X-MCBench-Identification"],
)

app.include_router(user_router)
app.include_router(comparison_router)


@app.get("/scalar", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="MC Bench API",
    )
