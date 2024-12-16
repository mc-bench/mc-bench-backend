from mc_bench.constants import GENERATION_STATE, RUN_STAGE_STATE, RUN_STATE

from ._base import Event


class RunStageStateChanged(Event):
    stage_id: int
    new_state: RUN_STAGE_STATE


class RunStateChanged(Event):
    run_id: int
    new_state: RUN_STATE


class GenerationStateChanged(Event):
    generation_id: int
    new_state: GENERATION_STATE
