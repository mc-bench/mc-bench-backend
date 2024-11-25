import re
import time

from sqlalchemy import select

from mc_bench.models.run import RUN_STATE, Run, Sample, run_state_id_for
from mc_bench.util.postgres import get_managed_session

from ..app import app


@app.task(name="run.execute_prompt")
def execute_prompt(
    run_id,
):
    with get_managed_session() as db:
        run = db.scalar(select(Run).where(Run.id == run_id))

        response = run.model.default_provider.execute_prompt(
            template=run.template, prompt=run.prompt
        )

        sample_kwargs = {
            "created_by": run.created_by,
            "run_id": run.id,
            "raw": response,
        }

        sample = Sample(**sample_kwargs)
        db.add(sample)
        db.commit()

        run.state_id = run_state_id_for(db, RUN_STATE.PROMPT_COMPLETED)
        db.commit()

        db.refresh(sample)

        return sample.id


@app.task(name="run.parse_prompt")
def parse_prompt(
    sample_id,
):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    with get_managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))

        print("sample: ", sample)
        print("sample.raw:", sample.raw)

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
            new_state = run_state_id_for(db, RUN_STATE.PROMPT_PROCESSING_FAILED)
        else:
            new_state = run_state_id_for(db, RUN_STATE.PROMPT_COMPLETED)

        db.commit()
        run.state_id = new_state
        db.commit()

        if new_state == run_state_id_for(db, RUN_STATE.PROMPT_PROCESSING_FAILED):
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


@app.task(name="run.build_structure")
def build_structure(sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    time.sleep(15)

    with get_managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))

        run.state_id = run_state_id_for(db, RUN_STATE.BUILD_COMPLETED)
        db.commit()

        # app.send_task(
        #     "run.post_processing",
        #     kwargs=dict(
        #         run_id=run.id,
        #     ),
        #     queue="admin",
        # )

        run.state_id = run_state_id_for(db, RUN_STATE.POST_PROCESSING_ENQUEUED)
        db.commit()

        return sample_id


@app.task(name="run.post_processing")
def post_process_build(sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    time.sleep(15)

    with get_managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))

        run.state_id = run_state_id_for(db, RUN_STATE.POST_PROCESSING_COMPLETED)
        db.commit()

        # app.send_task(
        #     "run.sample_prep",
        #     kwargs=dict(
        #         run_id=run.id,
        #     ),
        #     queue="admin",
        # )

        run.state_id = run_state_id_for(db, RUN_STATE.SAMPLE_PREP_ENQUEUED)
        db.commit()

        return sample_id


@app.task(name="run.sample_prep")
def prepare_sample(sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    time.sleep(15)

    with get_managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))

        run.state_id = run_state_id_for(db, RUN_STATE.COMPLETED)
        db.commit()

        return sample_id
