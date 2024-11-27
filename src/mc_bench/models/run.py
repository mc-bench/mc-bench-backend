import enum
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Mapped, object_session, relationship

import mc_bench.schema.postgres as schema

from ._base import Base


# Any values added here must also be added to the DB via a migration
# see d618a24f0bed_add_generation_state_and_run_state_.py for an example
class RUN_STATE(enum.Enum):
    CREATED = "CREATED"
    PROMPT_ENQUEUED = "PROMPT_ENQUEUED"
    PROMPT_COMPLETED = "PROMPT_COMPLETED"
    PROMPT_PROCESSING_ENQUEUED = "PROMPT_PROCESSING_ENQUEUED"
    PROMPT_PROCESSING_COMPLETED = "PROMPT_PROCESSING_COMPLETED"
    BUILD_ENQUEUED = "BUILD_ENQUEUED"
    BUILD_COMPLETED = "BUILD_COMPLETED"
    POST_PROCESSING_ENQUEUED = "POST_PROCESSING_ENQUEUED"
    POST_PROCESSING_COMPLETED = "POST_PROCESSING_COMPLETED"
    SAMPLE_PREP_ENQUEUED = "SAMPLE_PREP_ENQUEUED"
    COMPLETED = "COMPLETED"
    PROMPT_FAILED = "PROMPT_FAILED"
    PROMPT_PROCESSING_FAILED = "PROMPT_PROCESSING_FAILED"
    BUILD_FAILED = "BUILD_FAILED"
    POST_PROCESSING_FAILED = "POST_PROCESSING_FAILED"
    SAMPLE_PREP_FAILED = "SAMPLE_PREP_FAILED"


# Any values added here must also be added to the DB via a migration
# see d618a24f0bed_add_generation_state_and_run_state_.py for an example
class GENERATION_STATE(enum.Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    FAILED = "FAILED"


_run_state_cache: Dict[RUN_STATE, int] = {}
_generation_state_cache: Dict[RUN_STATE, int] = {}


# TODO: cache the result on `state`
def run_state_id_for(db, state: RUN_STATE):
    if state not in _run_state_cache:
        _run_state_cache[state] = db.scalar(
            select(RunState.id).where(RunState.slug == state.value)
        )
    return _run_state_cache[state]


# TODO: cache the result `state`
def generation_state_id_for(db, state: GENERATION_STATE):
    if state not in _generation_state_cache:
        _generation_state_cache[state] = db.scalar(
            select(GenerationState.id).where(GenerationState.slug == state.value)
        )
    return _generation_state_cache[state]


class Run(Base):
    __table__ = schema.specification.run

    creator = relationship("User", foreign_keys=[schema.specification.run.c.created_by])
    most_recent_editor = relationship(
        "User", foreign_keys=[schema.specification.run.c.last_modified_by]
    )

    template: Mapped["Template"] = relationship(  # noqa: F821
        "Template", uselist=False, back_populates="runs"
    )
    prompt: Mapped["Prompt"] = relationship(  # noqa: F821
        "Prompt", uselist=False, back_populates="runs"
    )
    model: Mapped["Model"] = relationship("Model", uselist=False, back_populates="runs")  # noqa: F821

    generation = relationship("Generation", uselist=False, back_populates="runs")

    state: Mapped["RunState"] = relationship("RunState", uselist=False)

    samples: Mapped[List["Sample"]] = relationship(
        "Sample", uselist=True, back_populates="run"
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", uselist=True, back_populates="run"
    )

    def to_dict(self, include_samples=False, include_artifacts=False):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.creator.username,
            "last_modified": self.last_modified,
            "prompt": self.prompt.to_dict(),
            "model": self.model.to_dict(),
            "template": self.template.to_dict(),
            "status": self.state.slug,
            "generation_id": self.generation.external_id
            if self.generation_id
            else None,
        }

        if self.most_recent_editor is not None:
            ret["last_modified_by"] = self.most_recent_editor.username
        else:
            ret["last_modified_by"] = None

        if include_samples:
            ret["samples"] = [sample.to_dict() for sample in self.samples]

        if include_artifacts:
            ret["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]

        return ret


class Sample(Base):
    __table__ = schema.sample.sample

    run: Mapped["Run"] = relationship("Run", back_populates="samples")

    def to_dict(self):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "result_inspiration_text": self.result_inspiration_text,
            "result_description_text": self.result_description_text,
            "result_code_text": self.result_code_text,
            "raw": self.raw,
            "active": self.active,
        }

        if self.last_modified is not None:
            ret["last_modified"] = self.last_modified

        return ret


class Artifact(Base):
    __table__ = schema.sample.artifact

    kind: Mapped["ArtifactKind"] = relationship("ArtifactKind")
    run: Mapped["Run"] = relationship("Run", back_populates="artifacts")

    def to_dict(self):
        return {
            "id": self.external_id,
            "kind": self.kind.name,
            "created": self.created,
            "bucket": self.bucket.name,
            "key": self.key,
        }


class ArtifactKind(Base):
    __table__ = schema.sample.artifact_kind


class Generation(Base):
    __table__ = schema.specification.generation

    creator = relationship(
        "User", foreign_keys=[schema.specification.generation.c.created_by]
    )

    runs: Mapped[List["Run"]] = relationship(  # noqa: F821
        "Run", uselist=True, back_populates="generation"
    )

    state: Mapped["GenerationState"] = relationship("GenerationState")

    @property
    def _run_count_expression(self):
        return select(func.count(1)).where(
            schema.specification.run.c.generation_id == self.id
        )

    @property
    def run_count(self):
        session = object_session(self)
        return session.scalar(self._run_count_expression)

    def to_dict(self, include_runs=False, include_stats=False):
        result = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.creator.username,
            "name": self.name,
            "description": self.description,
            "run_count": self.run_count,
            "status": self.state.slug,
        }

        if include_runs:
            result["runs"] = [
                run.to_dict() for run in sorted(self.runs, key=lambda x: x.created)
            ]

        if include_stats:
            # TODO: Implement this logic once run state changes are active
            result["pending_runs"] = 0
            result["completed_runs"] = 0
            result["failed_runs"] = 0

        return result


class GenerationState(Base):
    __table__ = schema.specification.generation_state


class RunState(Base):
    __table__ = schema.specification.run_state
