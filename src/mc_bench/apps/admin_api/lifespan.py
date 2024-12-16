from contextlib import asynccontextmanager

from mc_bench.events import on_event
from mc_bench.events.types import (
    GenerationStateChanged,
    RunStageStateChanged,
    RunStateChanged,
)
from mc_bench.models.run import Generation, Run, RunStage
from mc_bench.util.postgres import get_session


@asynccontextmanager
async def lifespan(app):
    session = get_session()
    engine = session.bind

    on_event(RunStageStateChanged, RunStage.state_change_handler)
    on_event(RunStateChanged, Run.state_change_handler)
    on_event(GenerationStateChanged, Generation.state_change_handler)

    yield

    # Close all connections and dispose of the engine
    engine.dispose()
