from typing import Optional

from celery import Celery
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.clients.mcbench_admin_api import Client
from mc_bench.constants import RUN_STAGE_STATE, RUN_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import RunStageStateChanged, RunStateChanged
from mc_bench.models.run import RunStage, Sample
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import managed_session

logger = get_logger(__name__)


class ValueNotSet:
    pass


def run_stage_task(
    name: str,
    app: Celery,
    stage: type[RunStage],
    terminal_stage: bool = False,
    retry_on_failure: bool = False,
    restart_run_on_failure: bool = False,
    max_reruns: int = 5,
    **kwargs,
):
    logger.info(
        "Configuring task",
        name=name,
        retry_on_failure=retry_on_failure,
        restart_run_on_failure=restart_run_on_failure,
    )
    if restart_run_on_failure and retry_on_failure:
        raise ValueError("Cannot restart run on failure if retry on failure is enabled")

    # TODO: Get task binding right
    def wrapper(func):
        @app.task(name=name, bind=True, **kwargs)
        def wrapped(self, metadata):
            logger.info("Metadata", metadata=metadata)
            run_id = metadata["run_id"]
            sample_id = metadata["sample_id"]

            logger.info("Starting task", name=name)
            logger.info("Task args", run_id=run_id, sample_id=sample_id)
            logger.info(
                "Task instance",
                retries=self.request.retries,
                max_retries=self.max_retries,
            )

            with managed_session() as db:
                api_client = Client(token=self.request.headers["token"])
                stage_context = StageContext(
                    admin_api_client=api_client,
                    task_id=self.request.id,
                    stage_class=stage,
                    run_id=run_id,
                    sample_id=sample_id,
                    db=db,
                )

                generation_id = stage_context.run.generation_id

                # THIS IS THE HAPPY PATH
                # 1. Emit the stage is in progress
                # 2. Run the stage
                # 3. Emit the stage is complete
                # 4. If terminal stage, emit we are completed
                try:
                    logger.info("Emitting IN_PROGRESS event")
                    emit_event(
                        RunStageStateChanged(
                            stage_id=stage_context.stage_id,
                            new_state=RUN_STAGE_STATE.IN_PROGRESS,
                        )
                    )
                    result = func(stage_context)
                    logger.info("Task completed successfully", result=result)
                    emit_event(
                        RunStageStateChanged(
                            stage_id=stage_context.stage_id,
                            new_state=RUN_STAGE_STATE.COMPLETED,
                        )
                    )
                    if terminal_stage:
                        stage_context.sample.is_complete = True
                        stage_context.sample.is_pending = False
                        db.add(stage_context.sample)
                        db.commit()

                        logger.info("Terminal stage, emitting COMPLETED")
                        emit_event(
                            RunStateChanged(
                                run_id=stage_context.run.id,
                                new_state=RUN_STATE.COMPLETED,
                            )
                        )
                    logger.info("Returning result", result=result)
                    return {
                        "run_id": result[0],
                        "sample_id": result[1],
                    }
                except Exception as e:
                    logger.error("Exception caught", error=e)
                    if retry_on_failure and self.max_retries > self.request.retries:
                        logger.info(
                            "Attempting retry",
                            retries=self.request.retries + 1,
                            max_retries=self.max_retries,
                        )
                        api_client.update_stage_progress(
                            run_external_id=stage_context.run.external_id,
                            stage=stage_context.stage_class.SLUG,
                            progress=0,
                            note=None,
                        )
                        emit_event(
                            RunStageStateChanged(
                                stage_id=stage_context.stage_id,
                                new_state=RUN_STAGE_STATE.IN_RETRY,
                            )
                        )
                        emit_event(
                            RunStateChanged(
                                run_id=stage_context.run.id,
                                new_state=RUN_STATE.IN_RETRY,
                            )
                        )
                        logger.info(
                            "Calling retry",
                            run_id=run_id,
                            sample_id=sample_id,
                        )
                        self.retry(
                            args=[
                                {
                                    "run_id": run_id,
                                    "sample_id": sample_id,
                                }
                            ],
                            exc=e,
                        )
                    elif (
                        restart_run_on_failure
                        and len(stage_context.run.samples) < max_reruns
                    ):
                        logger.info(
                            "Attempting run restart",
                            run_id=run_id,
                            sample_id=sample_id,
                            num_samples=len(stage_context.run.samples),
                            max_reruns=max_reruns,
                        )

                        stage_context.sample.is_complete = False
                        stage_context.sample.is_pending = False
                        db.add(stage_context.sample)
                        db.commit()

                        api_client.update_stage_progress(
                            run_external_id=stage_context.run.external_id,
                            stage=stage_context.stage_class.SLUG,
                            progress=0,
                            note=None,
                        )
                        emit_event(
                            RunStageStateChanged(
                                stage_id=stage_context.stage_id,
                                new_state=RUN_STAGE_STATE.IN_RETRY,
                            )
                        )
                        emit_event(
                            RunStateChanged(
                                run_id=stage_context.run.id,
                                new_state=RUN_STATE.IN_RETRY,
                            )
                        )
                        api_client.start_run_over(stage_context.run.external_id)
                        self.retry(
                            args=[
                                {
                                    "run_id": run_id,
                                    "sample_id": sample_id,
                                }
                            ],
                            exc=e,
                            max_retries=0,
                        )
                    else:
                        logger.info("Task failed permanently")
                        api_client.update_stage_progress(
                            run_external_id=stage_context.run.external_id,
                            stage=stage_context.stage_class.SLUG,
                            progress=0,
                            note=None,
                        )
                        emit_event(
                            RunStageStateChanged(
                                stage_id=stage_context.stage_id,
                                new_state=RUN_STAGE_STATE.FAILED,
                            )
                        )

                        stage_context.sample.is_complete = False
                        stage_context.sample.is_pending = False
                        db.add(stage_context.sample)
                        db.commit()

                        emit_event(
                            RunStateChanged(
                                run_id=stage_context.run.id,
                                new_state=RUN_STATE.FAILED,
                            )
                        )
                        self.retry(
                            args=[
                                {
                                    "run_id": run_id,
                                    "sample_id": sample_id,
                                }
                            ],
                            exc=e,
                            max_retries=0,
                        )

                finally:
                    if generation_id is not None:
                        app.signature(
                            "generation.finalize_generation",
                            args=[generation_id],
                            queue="admin",
                        ).apply_async()

        return wrapped

    return wrapper


class StageContext:
    """Context passed to stage execution with DB entities and metadata"""

    def __init__(
        self,
        admin_api_client: Client,
        task_id: str,
        stage_class: type[RunStage],
        run_id: int,
        sample_id: int,
        db: Session,
    ):
        self.admin_api_client = admin_api_client
        self.task_id = task_id
        self.stage_class = stage_class
        self.run_id = run_id
        self.sample_id = sample_id
        self.db = db
        self._run_stage: Optional[RunStage] = None

    @property
    def run_stage(self):
        if self._run_stage is None:
            self._run_stage = self.db.scalar(
                select(self.stage_class).where(self.stage_class.run_id == self.run_id)
            )

        return self._run_stage

    @property
    def stage_id(self):
        return self.run_stage.id

    @property
    def run(self):
        return self.run_stage.run

    @property
    def sample(self):
        if self.sample_id is None:
            return None
        else:
            return self.db.scalar(select(Sample).where(Sample.id == self.sample_id))

    def update_stage_progress(self, progress: int, note: Optional[str] = None):
        self.admin_api_client.update_stage_progress(
            run_external_id=self.run.external_id,
            stage=self.stage_class.SLUG,
            progress=progress,
            note=note,
        )
