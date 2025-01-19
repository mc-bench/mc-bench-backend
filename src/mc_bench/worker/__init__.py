from sqlalchemy import select

from mc_bench.clients.mcbench_admin_api import Client
from mc_bench.constants import RUN_STAGE_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import RunStageStateChanged
from mc_bench.models.run import Run, Sample
from mc_bench.util.postgres import managed_session


def run_stage_error_handler(stage_class, stage_slug):
    def wrapper(self, exc, task_id, args, kwargs, einfo):
        if self.request.retries < self.max_retries:
            print(f"Task {task_id} is in retry, not marking as failed")
            return

        print(f"Task {task_id} failed: {exc}")

        admin_api_client = Client(
            token=self.request.headers["token"],
        )

        sample_id = args[0] if args else kwargs.get("sample_id")

        with managed_session() as db:
            sample = db.scalar(select(Sample).where(Sample.id == sample_id))
            run = db.scalar(select(Run).where(Run.id == sample.run_id))
            sample_id = sample.id
            run_id = run.id
            run_stage = db.scalar(
                select(stage_class).where(stage_class.run_id == run_id)
            )
            run_stage_id = run_stage.id
            admin_api_client.update_stage_progress(
                run_external_id=run.external_id,
                stage=stage_slug,
                progress=0,
                note=None,
            )
            emit_event(
                RunStageStateChanged(
                    stage_id=run_stage_id, new_state=RUN_STAGE_STATE.FAILED
                )
            )

    return wrapper


def run_stage_retry_handler(stage_class, stage_slug):
    def wrapper(self, exc, task_id, args, kwargs, einfo):
        print(f"Task {task_id} failed: {exc}")

        sample_id = args[0] if args else kwargs.get("sample_id")

        admin_api_client = Client(
            token=self.request.headers["token"],
        )

        with managed_session() as db:
            sample = db.scalar(select(Sample).where(Sample.id == sample_id))
            run = db.scalar(select(Run).where(Run.id == sample.run_id))
            sample_id = sample.id
            run_id = run.id
            run_stage = db.scalar(
                select(stage_class).where(stage_class.run_id == run_id)
            )
            run_stage_id = run_stage.id
            admin_api_client.update_stage_progress(
                run_external_id=run.external_id,
                stage=stage_slug,
                progress=0,
                note=None,
            )
            emit_event(
                RunStageStateChanged(
                    stage_id=run_stage_id, new_state=RUN_STAGE_STATE.IN_RETRY
                )
            )

    return wrapper
