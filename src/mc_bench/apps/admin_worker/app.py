from mc_bench.events import on_event
from mc_bench.events.types import (
    GenerationStateChanged,
    RunStageStateChanged,
    RunStateChanged,
)
from mc_bench.models.run import Generation, Run, RunStage
from mc_bench.util.celery import make_worker_celery_app
from mc_bench.util.logging import configure_logging

from .config import settings

configure_logging(humanize=settings.HUMANIZE_LOGS)

app = make_worker_celery_app(
    dict(
        worker_prefetch_multiplier=4,
    )
)

# Event handler registration
on_event(RunStageStateChanged, RunStage.state_change_handler)
on_event(RunStateChanged, Run.state_change_handler)
on_event(GenerationStateChanged, Generation.state_change_handler)
