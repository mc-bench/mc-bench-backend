import re
import time

from sqlalchemy import select

from mc_bench.models.run import (
    RUN_STAGE_STATE,
    RUN_STATE,
    PostProcessing,
    PreparingSample,
    PromptExecution,
    ResponseParsing,
    Run,
    Sample,
    run_stage_state_id_for,
    run_state_id_for,
)
from mc_bench.util.postgres import managed_session

from ..app import app


@app.task(
    name="run.execute_prompt",
    autoretry_for=(Exception,),
    retry_backoff=5,
    max_retries=5,
)
def execute_prompt(
    run_id,
):
    with managed_session() as db:
        run = db.scalar(select(Run).where(Run.id == run_id))
        run_stage = db.scalar(
            select(PromptExecution).where(PromptExecution.run_id == run_id)
        )

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS)
        db.add(run_stage)
        db.commit()

        response = run.model.default_provider.execute_prompt(
            prompt=run.template.render(
                build_specification=run.prompt.build_specification,
            )
        )

        sample_kwargs = {
            "created_by": run.created_by,
            "run_id": run.id,
            "raw": response,
        }

        sample = Sample(**sample_kwargs)
        db.add(sample)
        db.commit()
        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)
        db.commit()
        db.refresh(sample)
        return sample.id


@app.task(name="run.parse_prompt")
def parse_prompt(
    sample_id,
):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        run_stage = db.scalar(
            select(ResponseParsing).where(ResponseParsing.run_id == run.id)
        )

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS)
        db.add(run_stage)
        db.commit()

        # 2. Parse Response
        parsed = _parse_known_parts(sample.raw)

        if parsed.get("code"):
            print("Code in parsed")

            if "```" in parsed["code"]:
                start_index = parsed["code"].find("```")
                end_index = parsed["code"].index("```", start_index + 1)
                code = parsed["code"][start_index:end_index]
                code_lines = []
                for line in code.split("\n"):
                    if "```" in line:
                        continue
                    code_lines.append(line)
                print("num code lines: ", len(code_lines))
                parsed["code"] = "\n".join(code_lines)

            sample.result_code_text = parsed["code"].strip()

        if parsed.get("inspiration"):
            sample.result_inspiration_text = parsed["inspiration"].strip()

        if parsed.get("description"):
            sample.result_description_text = parsed["description"].strip()

        if not all(
            [parsed.get("code"), parsed.get("inspiration"), parsed.get("description")]
        ):
            new_state = run_stage_state_id_for(db, RUN_STAGE_STATE.FAILED)
        else:
            new_state = run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)

        db.commit()
        run_stage.state_id = new_state
        db.commit()

        if new_state == run_state_id_for(db, RUN_STAGE_STATE.FAILED):
            raise RuntimeError("Prompting didn't go well")

        return sample_id


def _parse_known_parts(text):
    tags = ["code", "inspiration", "description"]
    result = {}

    # Parse each tag
    for tag in tags:
        pattern = f"<{tag}>(.*?)</{tag}>"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches and matches[0]:
            result[tag] = matches[0]

    if not result.get("inspiration"):
        try:
            start_index = text.index("<inspiration>") + len("<inspiration>")
            end_index = text.index("<description>")
            result["inspiration"] = text[start_index:end_index].strip()
        except ValueError:
            pass

    if not result.get("description"):
        try:
            start_index = text.index("<description>") + len("<description>")
            end_index = text.index("<code>")
            result["description"] = text[start_index:end_index].strip()
        except ValueError:
            pass

    if not result.get("code"):
        try:
            start_index = text.index("<code>") + len("<code>")
            result["code"] = text[start_index:].strip()
        except ValueError:
            pass

    return result


@app.task(name="run.post_processing")
def post_process_build(sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        run_stage = db.scalar(
            select(PostProcessing).where(PostProcessing.run_id == run.id)
        )

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS)
        db.add(run_stage)
        db.commit()

        # TODO: Post processing

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)
        db.commit()

        return sample_id


@app.task(name="run.sample_prep")
def prepare_sample(sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    time.sleep(15)

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))

        run_stage = db.scalar(
            select(PreparingSample).where(PreparingSample.run_id == run.id)
        )

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS)
        db.add(run_stage)
        db.commit()

        # TODO: Prepare sample

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)
        run.state_id = run_state_id_for(db, RUN_STATE.COMPLETED)
        db.add(run_stage)
        db.commit()
