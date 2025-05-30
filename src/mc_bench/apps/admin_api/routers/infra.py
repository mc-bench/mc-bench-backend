import datetime
import json
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import JSONResponse
from redis import StrictRedis
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.apps.admin_api.transport_types.requests import (
    CancelConsumerRequest,
    SchedulerControlUpdateRequest,
    WorkerActionRequest,
)
from mc_bench.apps.admin_api.transport_types.responses import (
    CancelConsumerResponse,
    InfraStatusResponse,
    QueuedTaskResponse,
    QueueResponse,
    SchedulerControlResponse,
    SchedulerControlsListResponse,
    WorkerResponse,
    WorkerTaskResponse,
)
from mc_bench.auth.permissions import PERM
from mc_bench.models.run import Run, RunStage
from mc_bench.models.scheduler_control import SchedulerControl
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session
from mc_bench.util.redis import RedisDatabase, get_redis_database

from ..celery import celery
from ..config import settings

logger = get_logger(__name__)

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
    "generation",
    "prompt",
    "parse",
    "validate",
    "post_process",
    "prepare",
]


@infra_router.get("/status", response_model=InfraStatusResponse)
async def get_infra_status(
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CELERY)),
    db: Session = Depends(get_managed_session),
):
    """
    Get the status of all infrastructure components (workers and queues).
    """
    workers = get_workers(db)
    queues = get_queues(redis, db)

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
async def get_all_workers(
    db: Session = Depends(get_managed_session),
):
    """
    Get information about all Celery workers.
    """
    return get_workers(db)


@infra_router.get("/queues", response_model=List[QueueResponse])
async def get_all_queues(
    redis: StrictRedis = Depends(get_redis_database(RedisDatabase.CELERY)),
    db: Session = Depends(get_managed_session),
):
    """
    Get information about all queues and their pending tasks.
    """
    return get_queues(redis, db)


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


def get_workers(db: Session) -> List[WorkerResponse]:
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

    # Collect all task IDs from all active and reserved tasks
    all_task_ids = []
    worker_data = {}

    # First pass: collect task IDs and prepare worker data
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

        # Parse worker name for container and hostname info
        container_name = worker_name
        node_name = ""
        display_name = worker_name

        # Check if we have the expected format with '@'
        if "@" in worker_name:
            parts = worker_name.split("@", 1)
            container_name = parts[0]
            node_name = parts[1]
            display_name = f"{container_name}@{node_name}"

        # Store all worker data except tasks
        worker_data[worker_name] = {
            "tasks_info": tasks + reserved,
            "active_tasks": set(task.get("id", "") for task in tasks),
            "stats": worker_stats,
            "queues": queues,
            "container_name": container_name,
            "node_name": node_name,
            "display_name": display_name,
        }

        # Collect all task IDs
        for task in tasks + reserved:
            task_id = task.get("id", "")
            if task_id:
                all_task_ids.append(task_id)

    # Get a mapping of task_id to run_id for all collected task IDs in a single query
    task_id_mapping = get_task_id_mapping(db, all_task_ids)

    # Second pass: build worker responses with task information
    for worker_name, data in worker_data.items():
        worker_tasks = []

        for task in data["tasks_info"]:
            task_id = task.get("id", "")
            # Include run_id if this task is associated with a run
            run_id = task_id_mapping.get(task_id)

            worker_tasks.append(
                WorkerTaskResponse(
                    id=task_id,
                    name=task.get("name", ""),
                    started_at=datetime.datetime.fromtimestamp(
                        task.get("time-start", 0)
                    )
                    if task.get("time-start")
                    else None,
                    args=task.get("args", []),
                    kwargs=task.get("kwargs", {}),
                    status="active" if task_id in data["active_tasks"] else "reserved",
                    eta=datetime.datetime.fromisoformat(task.get("eta"))
                    if task.get("eta")
                    else None,
                    retries=task.get("retries", 0),
                    run_id=run_id,
                )
            )

        workers.append(
            WorkerResponse(
                id=worker_name,
                hostname=worker_name,
                status="online",
                display_name=data["display_name"],
                container_name=data["container_name"],
                node_name=data["node_name"],
                queues=data["queues"],
                concurrency=data["stats"].get("pool", {}).get("max-concurrency", 0),
                pool_size=len(data["stats"].get("pool", {}).get("processes", [])),
                tasks=worker_tasks,
                last_heartbeat=None,  # Could be derived if available in stats
                started_at=None,  # Could be derived if available in stats
            )
        )

    return sorted(
        workers, key=lambda x: tuple([sorted(x.queues), x.node_name, x.container_name])
    )


def get_task_id_mapping(db: Session, task_ids: List[str] = None) -> Dict[str, UUID]:
    """
    Get a mapping of task IDs to run external IDs.

    Args:
        db: The database session.
        task_ids: Optional list of task IDs to filter the query by. If provided,
                 only task_ids in this list will be included in the mapping.

    Returns:
        A dictionary mapping task_ids to run.external_id values.
    """
    # Base query joining RunStage to Run to get external_id
    query = (
        select(RunStage.task_id, Run.external_id)
        .join(Run, RunStage.run_id == Run.id)
        .where(RunStage.task_id.is_not(None))
    )

    # Apply task_ids filter if provided
    if task_ids:
        query = query.where(RunStage.task_id.in_(task_ids))

    # Execute query and build mapping
    result = db.execute(query).all()

    # Create mapping from results
    mapping = {row[0]: row[1] for row in result if row[0] and row[1]}

    return mapping


@infra_router.get("/scheduler/controls", response_model=SchedulerControlsListResponse)
async def get_scheduler_controls(
    db: Session = Depends(get_managed_session),
):
    """
    List all scheduler control settings.
    """
    # Get all controls from the database
    result = db.execute(
        select(
            SchedulerControl.key,
            SchedulerControl.value,
            SchedulerControl.description,
            SchedulerControl.created,
            SchedulerControl.last_modified,
        )
    ).all()

    controls = []
    for key, value_str, description, created, last_modified in result:
        # Parse the JSON value
        try:
            value = json.loads(value_str)
        except json.JSONDecodeError:
            value = value_str  # Fallback to raw string if not valid JSON

        controls.append(
            SchedulerControlResponse(
                key=key,
                value=value,
                description=description,
                created=created,
                last_modified=last_modified,
            )
        )

    return SchedulerControlsListResponse(controls=controls)


@infra_router.get("/scheduler/controls/{key}", response_model=SchedulerControlResponse)
async def get_scheduler_control(
    key: str = Path(..., description="The control key to retrieve"),
    db: Session = Depends(get_managed_session),
):
    """
    Get a specific scheduler control setting by key.
    """
    result = db.execute(
        select(
            SchedulerControl.key,
            SchedulerControl.value,
            SchedulerControl.description,
            SchedulerControl.created,
            SchedulerControl.last_modified,
        ).where(SchedulerControl.key == key)
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduler control with key '{key}' not found",
        )

    key, value_str, description, created, last_modified = result

    # Parse the JSON value
    try:
        value = json.loads(value_str)
    except json.JSONDecodeError:
        value = value_str  # Fallback to raw string if not valid JSON

    return SchedulerControlResponse(
        key=key,
        value=value,
        description=description,
        created=created,
        last_modified=last_modified,
    )


@infra_router.put("/scheduler/controls/{key}", response_model=SchedulerControlResponse)
async def update_scheduler_control(
    request: SchedulerControlUpdateRequest,
    key: str = Path(..., description="The control key to update"),
    db: Session = Depends(get_managed_session),
):
    """
    Update a scheduler control setting by key.
    """
    # Check if the key exists
    existing = db.execute(
        select(
            SchedulerControl.key,
            SchedulerControl.description,
            SchedulerControl.created,
        ).where(SchedulerControl.key == key)
    ).first()

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduler control with key '{key}' not found",
        )

    # Update the value
    description = (
        request.description if request.description is not None else existing.description
    )
    SchedulerControl.set_value(db, key, request.value, description)

    # Commit the transaction
    db.commit()

    # Get the updated record
    updated = db.execute(
        select(
            SchedulerControl.key,
            SchedulerControl.value,
            SchedulerControl.description,
            SchedulerControl.created,
            SchedulerControl.last_modified,
        ).where(SchedulerControl.key == key)
    ).first()

    key, value_str, description, created, last_modified = updated

    # Parse the JSON value
    try:
        value = json.loads(value_str)
    except json.JSONDecodeError:
        value = value_str  # Fallback to raw string if not valid JSON

    return SchedulerControlResponse(
        key=key,
        value=value,
        description=description,
        created=created,
        last_modified=last_modified,
    )


def get_queues(redis: StrictRedis, db: Session) -> List[QueueResponse]:
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
                    "task_ids": [],  # Track task IDs for batch lookup
                    "raw_tasks": {},  # Store raw task data for later processing
                }
            queue_dict[queue_name]["workers"].append(worker_name)

    for queue_name in BASE_QUEUE_NAMES:
        if queue_name not in queue_dict:
            queue_dict[queue_name] = {
                "name": queue_name,
                "workers": [],
                "count": 0,
                "tasks": [],
                "task_ids": [],
                "raw_tasks": {},
            }

    # First pass: collect all task IDs and task data
    all_task_ids = []

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
                logger.debug("Task data", task_data=task_data)
                try:
                    task = json.loads(task_data)
                    task_id = task["headers"].get("id", "")

                    if task_id:
                        all_task_ids.append(task_id)
                        queue_dict[queue_name]["task_ids"].append(task_id)
                        queue_dict[queue_name]["raw_tasks"][task_id] = task

                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    # Get mapping of task_id to run_id for all collected task IDs in a single efficient query
    task_id_mapping = get_task_id_mapping(db, all_task_ids)

    # Second pass: build task responses with run_id information
    for queue_name, queue_data in queue_dict.items():
        for task_id in queue_data["task_ids"]:
            task = queue_data["raw_tasks"][task_id]
            # Include run_id if this task is associated with a run
            run_id = task_id_mapping.get(task_id)

            # Extract task details
            queue_data["tasks"].append(
                QueuedTaskResponse(
                    id=task_id,
                    name=task["headers"].get("task", ""),
                    eta=datetime.datetime.fromisoformat(task["headers"].get("eta"))
                    if task["headers"].get("eta")
                    else None,
                    priority=task["properties"].get("priority", 0),
                    queued_at=datetime.datetime.fromisoformat(
                        task["headers"].get("enqueued_timestamp", "")
                    )
                    if task["headers"].get("enqueued_timestamp")
                    else None,
                    run_id=run_id,
                )
            )

        # Clean up temporary data
        del queue_data["task_ids"]
        del queue_data["raw_tasks"]

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

    # Sort queues by count in descending order
    queues.sort(key=lambda q: q.count, reverse=True)

    return queues
