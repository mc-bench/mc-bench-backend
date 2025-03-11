import datetime
import time
from typing import Dict, List

from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from mc_bench.apps.scheduler.config import refresh_settings, settings
from mc_bench.auth.permissions import PERM
from mc_bench.constants import RUN_STAGE_STATE, RUN_STATE, STAGE
from mc_bench.models.run import (
    Run,
    RunStage,
    run_stage_state_id_for,
    run_state_id_for,
    stage_id_for,
)
from mc_bench.models.user import User
from mc_bench.util.celery import make_client_celery_app
from mc_bench.util.logging import configure_logging, get_logger
from mc_bench.util.postgres import managed_session
from mc_bench.util.redis import get_redis_client

logger = get_logger(__name__)

QUEUE_MAPPING = {
    STAGE.PROMPT_EXECUTION: "prompt",
    STAGE.RESPONSE_PARSING: "parse",
    STAGE.CODE_VALIDATION: "validate",
    STAGE.BUILDING: "server",
    STAGE.RENDERING_SAMPLE: "render",
    STAGE.POST_PROCESSING: "post_process",
    STAGE.PREPARING_SAMPLE: "prepare",
}

PREVIOUS_STAGE_MAPPING = {
    STAGE.PROMPT_EXECUTION: None,
    STAGE.RESPONSE_PARSING: STAGE.PROMPT_EXECUTION,
    STAGE.CODE_VALIDATION: STAGE.RESPONSE_PARSING,
    STAGE.BUILDING: STAGE.CODE_VALIDATION,
    STAGE.RENDERING_SAMPLE: STAGE.BUILDING,
    STAGE.POST_PROCESSING: STAGE.RENDERING_SAMPLE,
    STAGE.PREPARING_SAMPLE: STAGE.POST_PROCESSING,
}

REVERSE_QUEUE_MAPPING = {v: k for k, v in QUEUE_MAPPING.items()}


def create_access_token(user_external_id: str) -> str:
    """
    Create an access token for run stage tasks with proper permissions.
    """
    # Prepare token data
    expires_delta = datetime.timedelta(days=2)
    expire_time = datetime.datetime.utcnow() + expires_delta

    # Define token payload
    token_data = {
        "sub": str(user_external_id),
        "exp": expire_time,
        "scopes": [
            # Permits the bearer to write run progress updates
            PERM.RUN.PROGRESS_WRITE,
            # Permits the bearer to retry runs
            PERM.RUN.ADMIN,  # TODO: Make a standalone retry permission
        ],
    }

    # Create the JWT token
    return jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def get_queue_lengths(redis) -> Dict[str, int]:
    """Get the length of each queue from Redis."""
    queue_lengths = {}
    for queue_name in QUEUE_MAPPING.values():
        queue_key = f"{queue_name}"
        queue_length = redis.llen(queue_key)
        queue_lengths[queue_name] = queue_length
    return queue_lengths


def get_queue_capacities(redis, max_queued_tasks: Dict[str, int]) -> List[str]:
    """Get the queue names with capacity for each queue."""
    queue_lengths = get_queue_lengths(redis)
    logger.debug("Queue Limits", max_queued_tasks=max_queued_tasks)
    logger.debug("Queue lengths", queue_lengths=queue_lengths)
    queue_capacities = []
    for queue_name, queue_length in queue_lengths.items():
        if queue_length < max_queued_tasks[queue_name]:
            queue_capacities.append(
                (queue_name, max_queued_tasks[queue_name] - queue_length)
            )
        else:
            logger.info("No queue capacity for queue", queue_name=queue_name)
    return queue_capacities


def get_pending_runs_for_stage_id(
    db: Session, stage: STAGE, limit: int = 1
) -> List[RunStage]:
    logger.info("Finding pending runs for stage", stage=stage.value)
    stage_id = stage_id_for(db, stage)
    pending_stage_runs = (
        db.query(RunStage.run_id).filter(
            RunStage.state_id == run_stage_state_id_for(db, RUN_STAGE_STATE.PENDING)
        )
    ).filter(RunStage.stage_id == stage_id)

    ready_runs_query = (
        db.query(Run)
        .filter(
            (Run.state_id == run_state_id_for(db, RUN_STATE.CREATED))
            | (Run.state_id == run_state_id_for(db, RUN_STATE.IN_PROGRESS))
            | (Run.state_id == run_state_id_for(db, RUN_STATE.IN_RETRY))
        )
        .filter(Run.id.in_(pending_stage_runs))
        .options(selectinload(Run.stages))
        .with_for_update(skip_locked=True)
    )

    previous_stage = PREVIOUS_STAGE_MAPPING[stage]
    if previous_stage is not None:
        previous_stage_id = stage_id_for(db, previous_stage)
        completed_previous_stage_runs = (
            db.query(RunStage.run_id)
            .filter(
                RunStage.state_id
                == run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)
            )
            .filter(RunStage.stage_id == previous_stage_id)
        )
        ready_runs_query = ready_runs_query.filter(
            Run.id.in_(completed_previous_stage_runs)
        )

    # Apply sorting strategy based on the configuration
    sorting_strategy = settings.RUN_SORTING_STRATEGY
    logger.info("Using run sorting strategy", strategy=sorting_strategy)

    if sorting_strategy == "CREATED_ASC":
        # Sort by creation time ascending (oldest first)
        ready_runs_query = ready_runs_query.order_by(Run.created)
    elif sorting_strategy == "CREATED_DESC":
        # Sort by creation time descending (newest first)
        ready_runs_query = ready_runs_query.order_by(Run.created.desc())
    elif sorting_strategy == "RANDOM":
        # Use random sorting
        ready_runs_query = ready_runs_query.order_by(func.random())
    else:
        # Default to creation time ascending if strategy is not recognized
        logger.warning(
            "Unrecognized sorting strategy, defaulting to CREATED_ASC",
            strategy=sorting_strategy,
        )
        ready_runs_query = ready_runs_query.order_by(Run.created)

    ready_runs = ready_runs_query.limit(limit)

    # logger.debug(
    #     "ready query",
    #     query=str(ready_runs.statement.compile(compile_kwargs={"literal_binds": True})),
    # )

    runs = ready_runs.all()

    runs = [run.ready_stage for run in runs if run.ready_stage is not None]

    if runs:
        logger.info("Found runs to enqueue", run_ids=[run.id for run in runs])

    return runs


def find_and_handle_stalled_tasks(celery_app, db: Session) -> bool:
    """
    Find any IN_PROGRESS stages that have missed their heartbeat,
    revoke their tasks, and mark them as FAILED.

    Uses an optimized query to efficiently identify stalled tasks,
    even when dealing with a large number of stages.

    Returns:
        bool: True if any stalled tasks were handled, False otherwise
    """
    logger.info("Finding stalled runs")
    # Get necessary state IDs
    in_progress_state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS)
    failed_state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.FAILED)

    # Calculate heartbeat timeout threshold using database time
    # Use a SQL function to get the current database timestamp to prevent clock skew
    # Cast the return to timezone-naive datetime to match the heartbeat column
    current_db_time = db.scalar(select(func.now().label("now")))
    if current_db_time.tzinfo is not None:
        # Convert to naive datetime if it's timezone-aware
        current_db_time = current_db_time.replace(tzinfo=None)

    timeout_threshold = current_db_time - datetime.timedelta(
        seconds=settings.HEARTBEAT_TIMEOUT_SECONDS
    )

    # Find all IN_PROGRESS stages with stale heartbeats or no heartbeat
    # Use an index-optimized query for better performance with large datasets
    # Order by oldest heartbeat first to prioritize the most stalled tasks
    stalled_stages = db.scalars(
        select(RunStage)
        .where(RunStage.state_id == in_progress_state_id)
        .where((RunStage.heartbeat < timeout_threshold))
        .where(RunStage.task_id != None)  # Only consider stages with a task ID
        .order_by(RunStage.heartbeat.asc())
        .limit(settings.MAX_STALLED_TASKS_PER_CHECK)  # Use configurable limit
        .with_for_update(skip_locked=True)
    ).all()

    if not stalled_stages:
        return False

    logger.info(
        f"Found {len(stalled_stages)} stalled tasks that missed their heartbeat"
    )
    celery_app = make_client_celery_app()

    # Group stages by run_id to minimize run state updates
    runs_with_stalled_stages = {}

    if stalled_stages:
        logger.info(
            "Processing stalled runs",
            run_ids=[stage.run.id for stage in stalled_stages],
        )

    for stage in stalled_stages:
        run_id = stage.run.id
        stage_id = stage.id
        task_id = stage.task_id
        stage_slug = stage.stage.slug

        # Track which runs have stalled stages
        if run_id not in runs_with_stalled_stages:
            runs_with_stalled_stages[run_id] = []
        runs_with_stalled_stages[run_id].append(stage_id)

        # Calculate how long the stage has been stalled
        stall_duration = "unknown"
        if stage.heartbeat:
            stall_seconds = (current_db_time - stage.heartbeat).total_seconds()
            stall_duration = f"{stall_seconds:.1f}s"

        logger.warning(
            f"Stage {stage_id} (run {run_id}, {stage_slug}) has missed its heartbeat. "
            f"Last heartbeat: {stage.heartbeat} (stalled for {stall_duration}). "
            f"Revoking task {task_id} and marking as FAILED"
        )

        # Try to revoke the Celery task
        try:
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Successfully revoked task {task_id} for stage {stage_id}")
        except Exception as e:
            logger.exception(
                f"Error revoking task {task_id} for stage {stage_id}: {str(e)}"
            )

        # Mark the stage as FAILED using database time for consistency
        stage.state_id = failed_state_id
        # We don't need to set last_modified as it will be handled by the database's now() function

        # Clear the task_id since it's been revoked
        stage.task_id = None

    # Commit all changes
    db.commit()

    # Now handle the failed stages to update run state
    find_and_handle_failed_stages(celery_app, db)


def find_and_handle_failed_stages(celery_app, db: Session) -> bool:
    """
    Find any stages marked as FAILED where the run is not yet marked as FAILED.
    Update the run state and trigger generation finalization.

    Uses an optimized query approach to efficiently handle failure cases,
    including de-duplication of runs to avoid redundant processing.

    Returns:
        bool: True if any failed stages were handled, False otherwise
    """
    logger.info("Finding and handling failed runs")
    # Get necessary state IDs
    failed_stage_state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.FAILED)
    failed_run_state_id = run_state_id_for(db, RUN_STATE.FAILED)

    # Use a more advanced query to get distinct runs that have failed stages
    # This avoids processing multiple stages from the same run independently
    run_subquery = (
        select(RunStage.run_id)
        .where(RunStage.state_id == failed_stage_state_id)
        .group_by(RunStage.run_id)
    )

    # Find all runs with FAILED stages where the run is not FAILED
    # This is a more efficient approach than processing stages individually
    failed_runs = db.scalars(
        select(Run)
        .where(Run.id.in_(run_subquery))
        .where(Run.state_id != failed_run_state_id)
        .limit(settings.MAX_FAILED_STAGES_PER_CHECK)  # Use configurable limit
        .with_for_update(skip_locked=True)  # Skip locked runs to avoid contention
    ).all()

    if not failed_runs:
        return False

    logger.info(
        f"Found {len(failed_runs)} runs with failed stages not marked as failed"
    )

    generation_tasks = []  # Collect generation IDs to process in batch

    if failed_runs:
        logger.info("Processing failed runs", run_ids=[run.id for run in failed_runs])

    for run in failed_runs:
        run_id = run.id
        generation_id = run.generation_id
        failed_stages = [
            s for s in run.stages if s.state.slug == RUN_STAGE_STATE.FAILED.value
        ]

        # Log details about which stages failed
        failed_stage_info = ", ".join(
            [f"{s.id} ({s.stage.slug})" for s in failed_stages[:3]]
        )
        if len(failed_stages) > 3:
            failed_stage_info += f" and {len(failed_stages) - 3} more"

        logger.info(
            f"Handling run {run_id} with failed stages: {failed_stage_info} - "
            f"marking run as FAILED"
        )

        # Update the run state to FAILED, letting the database handle timestamps
        run.state_id = failed_run_state_id
        # No need to set last_modified, it will use the database's now() function

        # Finalize any samples in the run that are pending
        for sample in run.samples:
            if sample.is_pending:
                logger.debug(f"Marking sample {sample.id} as not pending")
                sample.is_pending = False
                sample.is_complete = False

        # Track generation IDs to finalize (avoid duplicate tasks)
        if generation_id and generation_id not in generation_tasks:
            generation_tasks.append(generation_id)

    # Commit all run changes
    db.commit()

    # Now enqueue generation finalization tasks in batch if we have any
    if generation_tasks:
        logger.info(
            f"Enqueueing generation finalization tasks for {len(generation_tasks)} generations"
        )

        for generation_id in generation_tasks:
            try:
                finalize_task = celery_app.signature(
                    "generation.finalize_generation",
                    args=[generation_id],
                    queue="generation",
                    headers={
                        "enqueued_timestamp": datetime.datetime.now(
                            tz=datetime.timezone.utc
                        ).isoformat()
                    },
                )
                finalize_task.apply_async()
                logger.debug(
                    f"Generation finalization task enqueued for generation {generation_id}"
                )
            except Exception as e:
                logger.exception(
                    f"Error enqueueing generation finalization task for generation {generation_id}: {str(e)}"
                )

        logger.info("Successfully enqueued all generation finalization tasks")

    return True


def scheduler_loop():
    """
    Main scheduler loop that runs continuously.

    Args:
        max_queued_tasks: Dict mapping queue names to max tasks
        interval: Sleep interval between scheduler runs in seconds
    """

    redis = get_redis_client()
    loop_count = 0
    celery_app = make_client_celery_app()

    with managed_session() as db:
        system_user_external_id = (
            db.scalars(select(User).where(User.id == 1)).one().external_id
        )

    while True:
        start_time = time.monotonic()

        with managed_session() as db:
            refresh_settings()
            max_queued_tasks = {
                queue: getattr(
                    settings,
                    f"MAX_TASKS_{queue.upper()}",
                    settings.DEFAULT_MAX_QUEUED_TASKS,
                )
                for queue in QUEUE_MAPPING.values()
            }
            interval = settings.SCHEDULER_INTERVAL

            if settings.get_scheduler_mode(db) != "on":
                logger.info(
                    f"Scheduler is in '{settings.get_scheduler_mode(db)}' mode, skipping this iteration"
                )
                time.sleep(interval)
                continue

            queue_capacities = get_queue_capacities(redis, max_queued_tasks)
            logger.info("Queue Capacities", queue_capacities=dict(queue_capacities))

            for queue_name, queue_capacity in queue_capacities:
                stage = REVERSE_QUEUE_MAPPING[queue_name]
                stages = get_pending_runs_for_stage_id(db, stage, limit=queue_capacity)
                for stage in stages:
                    stage.state_id = run_stage_state_id_for(
                        db, RUN_STAGE_STATE.ENQUEUED
                    )
                    db.commit()
                    progress_token = create_access_token(system_user_external_id)
                    task_signature = stage.get_task_signature(
                        celery_app, progress_token, pass_args=True
                    )
                    task = task_signature.apply_async()
                    stage.task_id = task.id
                    db.commit()

            find_and_handle_failed_stages(celery_app, db)
            find_and_handle_stalled_tasks(celery_app, db)

        time_taken = time.monotonic() - start_time
        if time_taken < interval:
            loop_count += 1
            logger.info(
                f"Completed loop {loop_count} in {time_taken:.2f}s",
                sleep_time=interval - time_taken,
            )
            time.sleep(interval - time_taken)


def main():
    """
    Main entry point for the scheduler.
    """
    # Configure logger with settings
    configure_logging(
        humanize=settings.HUMANIZE_LOGS,
        level=settings.LOG_LEVEL,
    )

    logger.info("Starting scheduler")
    logger.info(f"Default max tasks per queue: {settings.DEFAULT_MAX_QUEUED_TASKS}")
    logger.info(f"Scheduler interval: {settings.SCHEDULER_INTERVAL} seconds")

    scheduler_loop()
