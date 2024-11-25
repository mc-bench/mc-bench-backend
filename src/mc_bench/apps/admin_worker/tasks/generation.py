import celery
from sqlalchemy import select, text

from mc_bench.models.run import (
    GENERATION_STATE,
    RUN_STATE,
    Generation,
    Run,
    generation_state_id_for,
    run_state_id_for,
)
from mc_bench.util.postgres import get_session

from ..app import app


@app.task(name="generation.create_runs")
def create_runs(
    generation_id=None,
    prompt_ids=None,
    template_ids=None,
    model_ids=None,
):
    db = get_session()
    generation = db.scalar(select(Generation).where(Generation.id == generation_id))

    for template_id in template_ids:
        for prompt_id in prompt_ids:
            for model_id in model_ids:
                run = Run(
                    generation_id=generation_id,
                    created_by=generation.created_by,
                    template_id=template_id,
                    prompt_id=prompt_id,
                    model_id=model_id,
                    state_id=run_state_id_for(db, RUN_STATE.CREATED),
                )
                db.add(run)
    db.commit()

    run_ids = db.scalars(select(Run.id).where(Run.generation_id == generation_id)).all()
    workflow = celery.chain(
        celery.group(
            celery.chain(
                app.signature("run.execute_prompt", args=[run_id], queue="admin"),
                app.signature("run.parse_prompt", queue="admin"),
                app.signature("run.build_structure", queue="admin"),
                app.signature("run.post_processing", queue="admin"),
                app.signature("run.sample_prep", queue="admin"),
            )
            for run_id in run_ids
        ),
        app.signature(
            "generation.finalize_generation",
            args=[generation_id],
            queue="admin",
            immutable=True,
        ),
    )

    workflow.apply_async()
    db.execute(
        text("""\
    UPDATE specification.run 
    SET state_id = :new_state_id 
    WHERE id in :run_ids 
    AND state_id = :created_state_id;
    """).bindparams(
            run_ids=run_ids,
            new_state_id=run_state_id_for(db, RUN_STATE.PROMPT_ENQUEUED),
            created_state_id=run_state_id_for(db, RUN_STATE.CREATED),
        )
    )
    db.commit()

    return {
        "ok": True,
    }


@app.task(name="generation.finalize_generation")
def finalize_generation(generation_id):
    db = get_session()
    generation = db.scalar(select(Generation).where(Generation.id == generation_id))
    generation.state_id = generation_state_id_for(db, GENERATION_STATE.COMPLETED)
    db.commit()
