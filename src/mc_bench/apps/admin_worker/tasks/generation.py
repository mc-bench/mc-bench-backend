from sqlalchemy import select, text

from mc_bench.models.run import RUN_STATE, Generation, Run, run_state_id_for
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
                app.send_task(
                    "run.execute_prompt",
                    kwargs=dict(
                        run_id=run.id,
                    ),
                    queue="admin",
                )
                db.execute(
                    text("""\
                UPDATE specification.run 
                SET state_id = :new_state_id 
                WHERE id = :run_id 
                AND state_id = :created_state_id;
                """).bindparams(
                        run_id=run.id,
                        new_state_id=run_state_id_for(db, RUN_STATE.PROMPT_ENQUEUED),
                        created_state_id=run_state_id_for(db, RUN_STATE.CREATED),
                    )
                )
                db.commit()

    return {
        "ok": True,
    }
