import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from mc_bench.apps.admin_api.celery import send_task
from mc_bench.apps.admin_api.routers.templates import template_router
from mc_bench.util.postgres import get_session
from mc_bench.util.redis import RedisDatabase, get_redis_client

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOWED_ORIGIN").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(template_router)


@app.get("/")
def read_root():
    db = get_session()
    should_by_one = db.execute(text("select 1")).scalar()
    print(should_by_one)
    db.close()

    redis = get_redis_client(RedisDatabase.CACHE)
    redis_connected = bool(redis.ping())

    task = send_task("admin_example_task")
    task_result = task.get()

    return {
        "Hello": "World",
        "value": should_by_one,
        "redis_connected": redis_connected,
        "task_result": task_result,
    }
