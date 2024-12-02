import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mc_bench.apps.admin_api.routers.generations import generation_router
from mc_bench.apps.admin_api.routers.models import model_router
from mc_bench.apps.admin_api.routers.prompts import prompt_router
from mc_bench.apps.admin_api.routers.runs import run_router
from mc_bench.apps.admin_api.routers.templates import template_router

from .lifespan import lifespan

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOWED_ORIGIN").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(template_router)
app.include_router(prompt_router)
app.include_router(model_router)
app.include_router(generation_router)
app.include_router(run_router)
