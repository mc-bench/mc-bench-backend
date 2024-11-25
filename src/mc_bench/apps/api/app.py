import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mc_bench.apps.api.routers.user import user_router

allow_origins = os.environ.get("CORS_ALLOWED_ORIGIN", "").split(",")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
