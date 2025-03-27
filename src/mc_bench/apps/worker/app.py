from mc_bench.util.celery import make_worker_celery_app
from mc_bench.util.logging import configure_logging

from .config import settings

configure_logging(humanize=settings.HUMANIZE_LOGS, level=settings.LOG_LEVEL)

app = make_worker_celery_app()

# Explicitly import tasks to ensure they're registered
import mc_bench.apps.worker.tasks

# List registered tasks
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)
logger.info(f"Registered tasks: {list(app.tasks.keys())}")
