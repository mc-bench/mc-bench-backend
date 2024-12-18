import datetime
import os
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Mapped, object_session, relationship

import mc_bench.schema.postgres as schema
from mc_bench.constants import GENERATION_STATE, RUN_STAGE_STATE, RUN_STATE, STAGE
from mc_bench.events.types import (
    GenerationStateChanged,
    RunStageStateChanged,
    RunStateChanged,
)
from mc_bench.schema.object_store.runs import KINDS, runs
from mc_bench.util.object_store import (
    get_client,
    get_object_as_bytesio,
)
from mc_bench.util.uuid import uuid_from_ints

from ._base import Base

_run_state_cache: Dict[RUN_STATE, int] = {}
_generation_state_cache: Dict[RUN_STATE, int] = {}
_run_stage_state_cache: Dict[RUN_STAGE_STATE, int] = {}
_stage_cache: Dict[STAGE, int] = {}


def run_state_id_for(db, state: RUN_STATE):
    if state not in _run_state_cache:
        _run_state_cache[state] = db.scalar(
            select(RunState.id).where(RunState.slug == state.value)
        )
    return _run_state_cache[state]


def run_stage_state_id_for(db, stage_state: RUN_STAGE_STATE):
    if stage_state not in _run_stage_state_cache:
        _run_stage_state_cache[stage_state] = db.scalar(
            select(RunStageState.id).where(RunStageState.slug == stage_state.value)
        )

    return _run_stage_state_cache[stage_state]


def stage_id_for(db, stage: STAGE):
    if stage not in _stage_cache:
        _stage_cache[stage] = db.scalar(
            select(Stage.id).where(Stage.slug == stage.value)
        )
    return _stage_cache[stage]


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

    stages: Mapped[List["RunStage"]] = relationship(
        "RunStage", uselist=True, back_populates="run"
    )

    def sorted_stages(self, sort_order):
        return sorted(self.stages, key=lambda x: sort_order.index(x.stage.slug))

    def to_dict(
        self,
        include_samples=False,
        include_artifacts=False,
        include_stages=False,
        db=None,
        redis=None,
    ):
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

        if include_stages:
            ret["stages"] = [stage.to_dict(redis=redis) for stage in self.stages]

        return ret

    def make_stages(self, db):
        pending_stage_state = run_stage_state_id_for(db, RUN_STAGE_STATE.PENDING)

        return [
            PromptExecution(
                run_id=self.id,
                stage_id=stage_id_for(db, STAGE.PROMPT_EXECUTION),
                state_id=pending_stage_state,
            ),
            ResponseParsing(
                run_id=self.id,
                stage_id=stage_id_for(db, STAGE.RESPONSE_PARSING),
                state_id=pending_stage_state,
            ),
            CodeValidation(
                run_id=self.id,
                stage_id=stage_id_for(db, STAGE.CODE_VALIDATION),
                state_id=pending_stage_state,
            ),
            Building(
                run_id=self.id,
                stage_id=stage_id_for(db, STAGE.BUILDING),
                state_id=pending_stage_state,
            ),
            ExportingContent(
                run_id=self.id,
                stage_id=stage_id_for(db, STAGE.EXPORTING_CONTENT),
                state_id=pending_stage_state,
            ),
            PostProcessing(
                run_id=self.id,
                stage_id=stage_id_for(db, STAGE.POST_PROCESSING),
                state_id=pending_stage_state,
            ),
            PreparingSample(
                run_id=self.id,
                stage_id=stage_id_for(db, STAGE.PREPARING_SAMPLE),
                state_id=pending_stage_state,
            ),
        ]

    def get_stage(self, name):
        for stage in self.stages:
            if stage.stage.slug == name:
                return name

    @classmethod
    def state_change_handler(cls, event: RunStateChanged):
        import mc_bench.util.postgres as postgres

        table = cls.__table__

        with postgres.managed_session() as db:
            run_state_id = run_state_id_for(db, event.new_state)
            db.execute(
                table.update()
                .where(table.c.id == event.run_id)
                .values(state_id=run_state_id)
            )

    def generate_correlation_id(self) -> str:
        template_id = self.template.id
        prompt_id = self.prompt.id
        assert template_id is not None
        assert prompt_id is not None

        return uuid_from_ints(template_id, prompt_id)


class Sample(Base):
    __table__ = schema.sample.sample

    run: Mapped["Run"] = relationship("Run", back_populates="samples")
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", uselist=True, back_populates="sample"
    )

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

    def get_command_list_artifact(self):
        command_lists = [
            artifact
            for artifact in self.artifacts
            if artifact.kind.name == KINDS.BUILD_COMMAND_LIST
        ]
        if command_lists:
            return command_lists[0]

    def get_build_summary_artifact(self):
        summaries = [
            artifact
            for artifact in self.artifacts
            if artifact.kind.name == KINDS.BUILD_SUMMARY
        ]
        if summaries:
            return summaries[0]

    def build_artifact_spec(self, db, structure_name):
        run_external_id = self.run.external_id
        sample_external_id = self.external_id

        return {
            "build_script": {
                "object_parts": {
                    "run_id": run_external_id,
                    "sample_id": sample_external_id,
                    "name": f'{self.run.external_id}_{self.external_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
                },
                "artifact_kind": db.scalar(
                    select(ArtifactKind).where(
                        ArtifactKind.name == "ORIGINAL_BUILD_SCRIPT_JS"
                    )
                ),
                "object_prototype": runs.get(
                    KINDS.RUN,
                    KINDS.SAMPLE,
                    KINDS.ARTIFACTS,
                    KINDS.ORIGINAL_BUILD_SCRIPT_JS,
                ),
            },
            "schematic": {
                "container_path": os.path.join(
                    "/data/plugins/WorldEdit/schematics", f"{structure_name}.schem"
                ),
                "host_file": f"{structure_name}.schem",
                "host_path_directory": f"/data/schematics/{self.id}/",
                "object_parts": {
                    "run_id": run_external_id,
                    "sample_id": sample_external_id,
                    "name": f'{self.run.external_id}_{self.external_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
                },
                "artifact_kind": db.scalar(
                    select(ArtifactKind).where(ArtifactKind.name == "BUILD_SCHEMATIC")
                ),
                "object_prototype": runs.get(
                    KINDS.RUN,
                    KINDS.SAMPLE,
                    KINDS.ARTIFACTS,
                    KINDS.BUILD_SCHEMATIC,
                ),
            },
            "command_list": {
                "container_path": "/data/commandList.json",
                "host_file": "commandList.json",
                "host_path_directory": f"/data/schematics/{self.id}/",
                "object_parts": {
                    "run_id": run_external_id,
                    "sample_id": sample_external_id,
                    "name": f'{self.run.external_id}_{self.external_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
                },
                "artifact_kind": db.scalar(
                    select(ArtifactKind).where(
                        ArtifactKind.name == "BUILD_COMMAND_LIST"
                    )
                ),
                "object_prototype": runs.get(
                    KINDS.RUN,
                    KINDS.SAMPLE,
                    KINDS.ARTIFACTS,
                    KINDS.BUILD_COMMAND_LIST,
                ),
            },
            "build_summary": {
                "container_path": "/data/summary.json",
                "host_file": "summary.json",
                "host_path_directory": f"/data/schematics/{self.id}/",
                "object_parts": {
                    "run_id": run_external_id,
                    "sample_id": sample_external_id,
                    "name": f'{self.run.external_id}_{self.external_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
                },
                "artifact_kind": db.scalar(
                    select(ArtifactKind).where(ArtifactKind.name == "BUILD_SUMMARY")
                ),
                "object_prototype": runs.get(
                    KINDS.RUN,
                    KINDS.SAMPLE,
                    KINDS.ARTIFACTS,
                    KINDS.BUILD_SUMMARY,
                ),
            },
        }

    def export_artifact_spec(self, db, structure_name):
        run_external_id = self.run.external_id
        sample_external_id = self.external_id

        spec = {
            "command_list_build_script": {
                "object_parts": {
                    "run_id": run_external_id,
                    "sample_id": sample_external_id,
                    "name": f'{self.run.external_id}_{self.external_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
                },
                "artifact_kind": db.scalar(
                    select(ArtifactKind).where(
                        ArtifactKind.name == KINDS.COMMAND_LIST_BUILD_SCRIPT_JS
                    )
                ),
                "object_prototype": runs.get(
                    KINDS.RUN,
                    KINDS.SAMPLE,
                    KINDS.ARTIFACTS,
                    KINDS.COMMAND_LIST_BUILD_SCRIPT_JS,
                ),
            },
            "timelapse": {
                "container_path": f"/data/processed/{structure_name}_timelapse.mp4",
                "host_file": f"{structure_name}_timelapse.mp4",
                "host_path_directory": f"/data/content/{self.id}/",
                "object_parts": {
                    "run_id": run_external_id,
                    "sample_id": sample_external_id,
                    "name": f'{self.run.external_id}_{self.external_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
                },
                "artifact_kind": db.scalar(
                    select(ArtifactKind).where(
                        ArtifactKind.name == KINDS.BUILD_CINEMATIC_MP4
                    )
                ),
                "object_prototype": runs.get(
                    KINDS.RUN,
                    KINDS.SAMPLE,
                    KINDS.ARTIFACTS,
                    KINDS.BUILD_CINEMATIC_MP4,
                ),
            },
        }

        for side in ["north", "south", "east", "west"]:
            spec[f"{side}side_capture"] = {
                "container_path": f"/data/{side}side_capture.png",
                "host_file": f"{side}side_capture.png",
                "host_path_directory": f"/data/content/{self.id}/",
                "object_parts": {
                    "run_id": run_external_id,
                    "sample_id": sample_external_id,
                    "name": f'{self.run.external_id}_{self.external_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
                },
                "artifact_kind": db.scalar(
                    select(ArtifactKind).where(
                        ArtifactKind.name
                        == getattr(KINDS, f"{side.upper()}SIDE_CAPTURE_PNG")
                    )
                ),
                "object_prototype": runs.get(
                    KINDS.RUN,
                    KINDS.SAMPLE,
                    KINDS.ARTIFACTS,
                    getattr(KINDS, f"{side.upper()}SIDE_CAPTURE_PNG"),
                ),
            }

        return spec


class Artifact(Base):
    __table__ = schema.sample.artifact

    kind: Mapped["ArtifactKind"] = relationship("ArtifactKind")
    run: Mapped["Run"] = relationship("Run", back_populates="artifacts")
    sample: Mapped["Sample"] = relationship(
        "Sample", uselist=False, back_populates="artifacts"
    )

    def to_dict(self):
        return {
            "id": self.external_id,
            "kind": self.kind.name,
            "created": self.created,
            "bucket": self.bucket,
            "key": self.key,
        }

    def download_artifact(self, client=None):
        if client is None:
            client = get_client()

        return get_object_as_bytesio(
            client=client,
            bucket_name=self.bucket,
            object_name=self.key,
        )


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

    @classmethod
    def state_change_handler(cls, event: GenerationStateChanged):
        import mc_bench.util.postgres as postgres

        table = cls.__table__

        with postgres.managed_session() as db:
            generation_state_id = generation_state_id_for(db, event.new_state)
            db.execute(
                table.update()
                .where(table.c.id == event.generation_id)
                .values(state_id=generation_state_id)
            )


class GenerationState(Base):
    __table__ = schema.specification.generation_state


class RunState(Base):
    __table__ = schema.specification.run_state


class Stage(Base):
    __table__ = schema.specification.stage


class RunStageState(Base):
    __table__ = schema.specification.run_stage_state


class RunStage(Base):
    __table__ = schema.specification.run_stage

    stage: Mapped[Stage] = relationship("Stage", foreign_keys="RunStage.stage_id")
    run: Mapped["Run"] = relationship("Run", back_populates="stages")
    state: Mapped["RunStageState"] = relationship("RunStageState", uselist=False)

    __mapper_args__ = {"polymorphic_on": "stage_slug"}

    def to_dict(self, db=None, redis=None):
        db = object_session(self)
        state = self.state
        progress_note = None
        if state.id in (
            run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS),
            run_stage_state_id_for(db, RUN_STAGE_STATE.IN_RETRY),
        ):
            progress, progress_note = self.get_stage_progress(redis)
        elif state.id == run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED):
            progress = 1.0
        else:
            progress = 0

        return {
            "id": self.external_id,
            "stage": self.stage.slug,
            "state": state.slug,
            "progress": progress,
            "note": progress_note,
        }

    def get_stage_progress(self, redis) -> float:
        progress = redis.get(f"stage:{self.id}:progress")
        progress_note = redis.get(f"stage:{self.id}:progress_note")
        return (float(progress) if progress else 0.0), progress_note

    def set_progress(self, redis, progress, note=None):
        redis.set(f"stage:{self.id}:progress", str(progress))
        if note:
            redis.set(f"stage:{self.id}:progress_note", note)
        else:
            try:
                redis.delete(f"stage:{self.id}:progress_note")
            except Exception:
                pass

    def get_task_signature(self, app, progress_token, pass_args=True):
        pass

    @classmethod
    def state_change_handler(cls, event: RunStageStateChanged):
        import mc_bench.util.postgres as postgres

        table = cls.__table__

        with postgres.managed_session() as db:
            run_stage_state_id = run_stage_state_id_for(db, event.new_state)
            db.execute(
                table.update()
                .where(table.c.id == event.stage_id)
                .values(state_id=run_stage_state_id)
            )


class PromptExecution(RunStage):
    __mapper_args__ = {
        "polymorphic_identity": "PROMPT_EXECUTION",
    }

    def get_task_signature(self, app, progress_token, pass_args=True):
        kwargs = {}
        kwargs["queue"] = "admin"
        kwargs["headers"] = {"token": progress_token}
        if pass_args:
            kwargs["args"] = [self.run_id]

        return app.signature("run.execute_prompt", **kwargs)


class ResponseParsing(RunStage):
    __mapper_args__ = {
        "polymorphic_identity": "RESPONSE_PARSING",
    }

    def get_task_signature(self, app, progress_token, pass_args=True):
        kwargs = {}
        kwargs["queue"] = "admin"
        kwargs["headers"] = {"token": progress_token}
        if pass_args:
            sample_id = self.run.samples[-1].id
            print(f"Setting sample_id: {sample_id}")
            kwargs["args"] = [sample_id]

        return app.signature("run.parse_prompt", **kwargs)


class CodeValidation(RunStage):
    __mapper_args__ = {
        "polymorphic_identity": "CODE_VALIDATION",
    }

    def get_task_signature(self, app, progress_token, pass_args=True):
        kwargs = {}
        kwargs["queue"] = "admin"
        kwargs["headers"] = {"token": progress_token}
        if pass_args:
            sample_id = self.run.samples[-1].id
            print(f"Setting sample_id: {sample_id}")
            kwargs["args"] = [sample_id]

        return app.signature("run.code_validation", **kwargs)


class Building(RunStage):
    __mapper_args__ = {
        "polymorphic_identity": "BUILDING",
    }

    def get_task_signature(self, app, progress_token, pass_args=True):
        kwargs = {}
        kwargs["queue"] = "server"
        kwargs["headers"] = {"token": progress_token}
        if pass_args:
            sample_id = self.run.samples[-1].id
            print(f"Setting sample_id: {sample_id}")
            kwargs["args"] = [sample_id]

        return app.signature("run.build_structure", **kwargs)


class ExportingContent(RunStage):
    __mapper_args__ = {
        "polymorphic_identity": "EXPORTING_CONTENT",
    }

    def get_task_signature(self, app, progress_token, pass_args=True):
        kwargs = {}
        kwargs["queue"] = "server"
        kwargs["headers"] = {"token": progress_token}
        if pass_args:
            sample_id = self.run.samples[-1].id
            print(f"Setting sample_id: {sample_id}")
            kwargs["args"] = [sample_id]

        return app.signature("run.export_structure_views", **kwargs)


class PostProcessing(RunStage):
    __mapper_args__ = {
        "polymorphic_identity": "POST_PROCESSING",
    }

    def get_task_signature(self, app, progress_token, pass_args=True):
        kwargs = {}
        kwargs["queue"] = "admin"
        kwargs["headers"] = {"token": progress_token}
        if pass_args:
            sample_id = self.run.samples[-1].id
            print(f"Setting sample_id: {sample_id}")
            kwargs["args"] = [sample_id]

        return app.signature("run.post_processing", **kwargs)


class PreparingSample(RunStage):
    __mapper_args__ = {
        "polymorphic_identity": "PREPARING_SAMPLE",
    }

    def get_task_signature(self, app, progress_token, pass_args=True):
        kwargs = {}
        kwargs["queue"] = "admin"
        kwargs["headers"] = {"token": progress_token}
        if pass_args:
            sample_id = self.run.samples[-1].id
            print(f"Setting sample_id: {sample_id}")
            kwargs["args"] = [sample_id]

        return app.signature("run.sample_prep", **kwargs)
