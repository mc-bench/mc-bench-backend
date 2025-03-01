import datetime
import json
from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis import StrictRedis

from mc_bench.apps.admin_api.transport_types.requests import (
    CancelConsumerRequest,
    WorkerActionRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    CancelConsumerResponse,
    InfraStatusResponse,
    QueuedTaskResponse,
    QueueResponse,
    WorkerResponse,
    WorkerTaskResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.server.auth import AuthManager
from mc_bench.util.redis import RedisDatabase, get_redis_database

from ..celery import celery
from ..config import settings

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)

infra_router = APIRouter(
    prefix="/api/infra",
    tags=["infrastructure"],
    dependencies=[
        Depends(am.require_any_scopes([PERM.RUN.ADMIN])),
    ],
)


BASE_QUEUE_NAMES = [
    "default",
    "render",
    "server",
    "admin",
]


@infra_router.get("/status", response_model=InfraStatusResponse)
async def get_infra_status(
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CELERY)),
):
    """
    Get the status of all infrastructure components (workers and queues).
    """
    workers = get_workers()
    queues = get_queues(redis)

    total_active_tasks = sum(len(worker.tasks) for worker in workers)
    total_queued_tasks = sum(queue.count for queue in queues)

    unserviced_queues = [queue.name for queue in queues if queue.worker_count == 0]

    return InfraStatusResponse(
        workers=workers,
        queues=queues,
        total_active_tasks=total_active_tasks,
        total_queued_tasks=total_queued_tasks,
        warnings=[f"Queue [{queue}] has no workers" for queue in unserviced_queues],
    )


@infra_router.get("/workers", response_model=List[WorkerResponse])
async def get_all_workers():
    """
    Get information about all Celery workers.
    """
    return get_workers()


@infra_router.get("/queues", response_model=List[QueueResponse])
async def get_all_queues(
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CELERY)),
):
    """
    Get information about all queues and their pending tasks.
    """
    return get_queues(redis)


@infra_router.post(
    "/workers/{worker_id}/cancel-consumer",
    response_model=CancelConsumerResponse,
)
async def cancel_consumer(worker_id: str, request: CancelConsumerRequest):
    """
    Cancel a worker's consumption from a specific queue.
    """
    try:
        # Use Celery's control interface to cancel the consumer
        response = celery.control.cancel_consumer(
            request.queue, destination=[worker_id]
        )

        if response and response[0].get(worker_id, {}).get("ok") == "ok":
            return CancelConsumerResponse(
                success=True,
                message=f"Worker {worker_id} has stopped consuming from {request.queue}",
            )
        else:
            return CancelConsumerResponse(
                success=False,
                message=f"Failed to cancel consumer for worker {worker_id}: {response}",
            )
    except Exception as e:
        return CancelConsumerResponse(
            success=False, message=f"Error cancelling consumer: {str(e)}"
        )


@infra_router.post(
    "/workers/{worker_id}/action",
)
async def worker_action(worker_id: str, request: WorkerActionRequest):
    """
    Perform an action on a worker (shutdown, restart, pool_grow, pool_shrink).
    """
    try:
        if request.action == "shutdown":
            response = celery.control.broadcast("shutdown", destination=[worker_id])
        elif request.action == "pool_grow":
            n = request.option if request.option is not None else 1
            response = celery.control.pool_grow(n=n, destination=[worker_id])
        elif request.action == "pool_shrink":
            n = request.option if request.option is not None else 1
            response = celery.control.pool_shrink(n=n, destination=[worker_id])
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Unknown action: {request.action}"},
            )

        return {"success": True, "response": response}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Error performing action: {str(e)}"},
        )


def get_workers() -> List[WorkerResponse]:
    """
    Get information about all Celery workers.
    """
    workers = []

    # Get active workers
    inspector = celery.control.inspect()
    active_workers = inspector.active()
    reserved_tasks = inspector.reserved()
    stats = inspector.stats()
    active_queues = inspector.active_queues()

    if active_workers is None:
        return workers

    for worker_name, tasks in active_workers.items():
        # Get reserved tasks for this worker
        reserved = reserved_tasks.get(worker_name, []) if reserved_tasks else []

        # Get stats for this worker
        worker_stats = stats.get(worker_name, {}) if stats else {}

        # Get queues from active_queues
        queues = []
        if active_queues and worker_name in active_queues:
            for queue_info in active_queues[worker_name]:
                queues.append(queue_info["name"])

        # Combine active and reserved tasks
        worker_tasks = []

        for task in tasks + reserved:
            worker_tasks.append(
                WorkerTaskResponse(
                    id=task.get("id", ""),
                    name=task.get("name", ""),
                    started_at=datetime.datetime.fromtimestamp(
                        task.get("time-start", 0)
                    )
                    if task.get("time-start")
                    else None,
                    args=task.get("args", []),
                    kwargs=task.get("kwargs", {}),
                    status="active" if task in tasks else "reserved",
                    eta=datetime.datetime.fromisoformat(task.get("eta"))
                    if task.get("eta")
                    else None,
                    retries=task.get("retries", 0),
                )
            )

        workers.append(
            WorkerResponse(
                id=worker_name,
                hostname=worker_name,
                status="online",
                queues=queues,
                concurrency=worker_stats.get("pool", {}).get("max-concurrency", 0),
                pool_size=len(worker_stats.get("pool", {}).get("processes", [])),
                tasks=worker_tasks,
                last_heartbeat=None,  # Could be derived if available in stats
                started_at=None,  # Could be derived if available in stats
            )
        )

    return sorted(workers, key=lambda x: tuple([sorted(x.queues), x.id]))


def get_queues(redis: StrictRedis) -> List[QueueResponse]:
    """
    Get information about all Celery queues and their pending tasks using Redis directly.
    """
    queues = []

    # Get all active workers for queue discovery
    inspector = celery.control.inspect()
    active_queues = inspector.active_queues()

    if active_queues is None:
        return queues

    # Collect unique queues from all workers
    queue_dict = {}
    for worker_name, worker_queues in active_queues.items():
        for queue_info in worker_queues:
            queue_name = queue_info["name"]
            if queue_name not in queue_dict:
                queue_dict[queue_name] = {
                    "name": queue_name,
                    "workers": [],
                    "count": 0,
                    "tasks": [],
                }
            queue_dict[queue_name]["workers"].append(worker_name)

    for queue_name in BASE_QUEUE_NAMES:
        if queue_name not in queue_dict:
            queue_dict[queue_name] = {
                "name": queue_name,
                "workers": [],
                "count": 0,
                "tasks": [],
            }

    # Directly inspect Redis queues
    for queue_name in queue_dict:
        # Get queue length - queue name is the key
        queue_length = redis.llen(queue_name)
        queue_dict[queue_name]["count"] = queue_length

        # Get task details (limited to 100)
        if queue_length > 0:
            # Get up to 100 tasks from the queue
            tasks = redis.lrange(queue_name, 0, 99)

            for task_data in tasks:
                try:
                    task = json.loads(task_data)

                    # Extract task details
                    queue_dict[queue_name]["tasks"].append(
                        QueuedTaskResponse(
                            id=task.get("id", ""),
                            name=task.get("task", ""),
                            args=task.get("args", []),
                            kwargs=task.get("kwargs", {}),
                            eta=datetime.datetime.fromisoformat(task.get("eta"))
                            if task.get("eta")
                            else None,
                            priority=task.get("priority", 0),
                            queued_at=datetime.datetime.fromtimestamp(
                                task.get("created", 0)
                            )
                            if task.get("created")
                            else None,
                        )
                    )
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    # Convert dictionary to list of QueueResponse objects
    queues = [
        QueueResponse(
            name=queue_name,
            worker_count=len(queue_data["workers"]),
            count=queue_data["count"],
            tasks=queue_data["tasks"],
        )
        for queue_name, queue_data in queue_dict.items()
    ]

    return queues
