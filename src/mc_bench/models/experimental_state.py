from typing import Dict

from sqlalchemy import select

import mc_bench.schema.postgres as schema
from mc_bench.constants import EXPERIMENTAL_STATE

from ._base import Base

_experimental_state_cache: Dict[EXPERIMENTAL_STATE, int] = {}


def experimental_state_id_for(db, state: EXPERIMENTAL_STATE):
    if state not in _experimental_state_cache:
        _experimental_state_cache[state] = db.scalar(
            select(ExperimentalState.id).where(ExperimentalState.name == state.value)
        )
    return _experimental_state_cache[state]


class ExperimentalState(Base):
    __table__ = schema.research.experimental_state

    def to_dict(self):
        return {
            "id": self.external_id,
            "name": self.name,
        }
