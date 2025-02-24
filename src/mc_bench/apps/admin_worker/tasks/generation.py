import celery
from sqlalchemy import select, text

from mc_bench.constants import GENERATION_STATE, RUN_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import GenerationStateChanged
from mc_bench.models.run import (
    Generation,
    Run,
    run_state_id_for,
)
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import managed_session

from ..app import app

logger = get_logger(__name__)


@app.task(bind=True, name="generation.create_runs")
def create_runs(
    self,
    generation_id=None,
    prompt_ids=None,
    template_ids=None,
    model_ids=None,
    num_samples=1,
):
    logger.info(f"Creating runs for generation {generation_id}")
    with managed_session() as db:
        generation = db.scalar(select(Generation).where(Generation.id == generation_id))

        for template_id in template_ids:
            for prompt_id in prompt_ids:
                for model_id in model_ids:
                    for _ in range(num_samples):
                        run = Run(
                            generation_id=generation_id,
                            created_by=generation.created_by,
                            template_id=template_id,
                            prompt_id=prompt_id,
                            model_id=model_id,
                            state_id=run_state_id_for(db, RUN_STATE.CREATED),
                        )
                        db.add(run)
                        db.flush()
                        logger.info(
                            "Run created",
                            template_id=template_id,
                            prompt_id=prompt_id,
                            model_id=model_id,
                        )
                        stages = run.make_stages(db)
                        logger.info(
                            "Stages created",
                            template_id=template_id,
                            prompt_id=prompt_id,
                            model_id=model_id,
                            run_id=run.id,
                        )
                        db.add_all(stages)
        db.commit()

        run_ids = db.scalars(
            select(Run.id).where(Run.generation_id == generation_id)
        ).all()

        headers = {"token": self.request.headers["token"]}

        workflow = celery.group(
            celery.chain(
                app.signature(
                    "run.execute_prompt",
                    args=[
                        {
                            "run_id": run_id,
                            "sample_id": None,
                        }
                    ],
                    queue="admin",
                    headers=headers,
                ),
                app.signature("run.parse_prompt", queue="admin", headers=headers),
                app.signature("run.code_validation", queue="admin", headers=headers),
                app.signature("run.build_structure", queue="server", headers=headers),
                app.signature("run.render_sample", queue="render", headers=headers),
                # TODO: Add exporting content back in once implemented in blender
                # app.signature(
                #     "run.export_structure_views", queue="server", headers=headers
                # ),
                app.signature("run.post_processing", queue="admin", headers=headers),
                app.signature("run.prepare_sample", queue="admin", headers=headers),
            )
            for run_id in run_ids
        )

        workflow.apply_async()

        db.execute(
            text("""\
        UPDATE specification.run 
        SET state_id = :new_state_id 
        WHERE id = ANY(:run_ids) 
        AND state_id = :created_state_id;
        """).bindparams(
                run_ids=run_ids,
                new_state_id=run_state_id_for(db, RUN_STATE.IN_PROGRESS),
                created_state_id=run_state_id_for(db, RUN_STATE.CREATED),
            )
        )
        db.commit()

        return {
            "ok": True,
        }


@app.task(name="generation.finalize_generation")
def finalize_generation(generation_id):
    logger.info("Finalizing generation", generation_id=generation_id)
    with managed_session() as db:
        run_states = db.scalars(
            select(Run.state_id).where(Run.generation_id == generation_id)
        ).all()

        if all(
            run_state == run_state_id_for(db, RUN_STATE.COMPLETED)
            for run_state in run_states
        ):
            logger.info("Generation completed", generation_id=generation_id)
            generation_state = GENERATION_STATE.COMPLETED
        elif any(
            run_state == run_state_id_for(db, RUN_STATE.IN_RETRY)
            for run_state in run_states
        ):
            logger.info("Generation in retry", generation_id=generation_id)
            generation_state = GENERATION_STATE.IN_RETRY
        elif all(
            run_state == run_state_id_for(db, RUN_STATE.FAILED)
            for run_state in run_states
        ):
            logger.info("Generation failed", generation_id=generation_id)
            generation_state = GENERATION_STATE.FAILED
        elif any(
            run_state == run_state_id_for(db, RUN_STATE.FAILED)
            for run_state in run_states
        ):
            logger.info("Generation partial failed", generation_id=generation_id)
            generation_state = GENERATION_STATE.PARTIAL_FAILED
        else:
            logger.info("Generation in progress", generation_id=generation_id)
            generation_state = GENERATION_STATE.IN_PROGRESS

        emit_event(
            GenerationStateChanged(
                generation_id=generation_id, new_state=generation_state
            )
        )
