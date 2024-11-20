import re

from sqlalchemy import select

from mc_bench.models.run import RUN_STATE, Run, run_state_id_for
from mc_bench.models.sample import Sample
from mc_bench.util.postgres import get_session

from ..app import app


@app.task(name="run.execute_prompt")
def execute_prompt(
    run_id=None,
):
    db = get_session()
    run = db.scalar(select(Run).where(Run.id == run_id))

    response = run.model.default_provider.execute_prompt(
        template=run.template, prompt=run.prompt
    )

    # 1. Upload raw response
    # 2. Parse Response
    parsed = _parse_known_parts(response)
    sample_kwargs = {
        "created_by": run.created_by,
        "run_id": run.id,
    }

    if parsed["code"]:
        sample_kwargs["result_code_text"] = parsed["code"]

    if parsed.get("inspiration"):
        sample_kwargs["result_inspiration_text"] = parsed["inspiration"]

    if parsed.get("description"):
        sample_kwargs["result_description_text"] = parsed["description"]

    sample = Sample(**sample_kwargs)
    db.add(sample)
    db.commit()

    run.state_id = run_state_id_for(db, RUN_STATE.PROMPT_COMPLETED)
    db.commit()

    # TODO:
    # send_task to build
    # run.run_state_id = run_state_id_for(db, RUN_STATE.BU)
    # db.add(run)
    # db.commit()

    return {
        "ok": True,
    }


def _parse_known_parts(text):
    tags = ["code", "inspiration", "description"]
    result = {}

    # Parse each tag
    for tag in tags:
        pattern = f"<{tag}>(.*?)</{tag}>"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches and matches[0]:
            result[tag] = matches[0]

    return result
