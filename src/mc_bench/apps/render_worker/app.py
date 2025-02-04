from mc_bench.events import on_event
from mc_bench.events.types import (
    GenerationStateChanged,
    RunStageStateChanged,
    RunStateChanged,
)
from mc_bench.models.run import Generation, Run, RunStage
from mc_bench.util.celery import make_worker_celery_app

app = make_worker_celery_app(
    dict(
        worker_prefetch_multiplier=1,
    )
)

# Event handler registration
on_event(RunStageStateChanged, RunStage.state_change_handler)
on_event(RunStateChanged, Run.state_change_handler)
on_event(GenerationStateChanged, Generation.state_change_handler)
