import time

from sqlalchemy import select

from mc_bench.constants import RUN_STAGE_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import RunStageStateChanged
from mc_bench.models.run import (
    PostProcessing,
    PreparingSample,
    PromptExecution,
    ResponseParsing,
    Run,
    Sample,
)
from mc_bench.util.postgres import managed_session
from mc_bench.util.text import parse_known_parts

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

        run_stage_id = run_stage.id
        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.IN_PROGRESS
            )
        )

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
        db.refresh(sample)
        sample_id = sample.id
        run_stage_id = run_stage.id

    emit_event(
        RunStageStateChanged(stage_id=run_stage_id, new_state=RUN_STAGE_STATE.COMPLETED)
    )

    return sample_id


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

        run_stage_id = run_stage.id
        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.IN_PROGRESS
            )
        )

        # 2. Parse Response
        parsed = parse_known_parts(sample.raw)

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

        db.commit()

        if not all(
            [parsed.get("code"), parsed.get("inspiration"), parsed.get("description")]
        ):
            new_state = RUN_STAGE_STATE.FAILED
        else:
            new_state = RUN_STAGE_STATE.COMPLETED

        emit_event(RunStageStateChanged(stage_id=run_stage_id, new_state=new_state))

        if new_state == RUN_STAGE_STATE.FAILED:
            raise RuntimeError("Prompting didn't go well")

        return sample_id


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

        run_stage_id = run_stage.id
        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.IN_PROGRESS
            )
        )

        # TODO: Post processing

        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.COMPLETED
            )
        )
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

        run_stage_id = run_stage.id
        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.IN_PROGRESS
            )
        )

        # TODO: Prepare sample

        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.COMPLETED
            )
        )
        return sample_id
