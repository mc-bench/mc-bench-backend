import os
import subprocess
import tempfile
import time

from sqlalchemy import select

from mc_bench.clients.mcbench_admin_api import Client
from mc_bench.constants import RUN_STAGE_STATE, RUN_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import RunStageStateChanged, RunStateChanged
from mc_bench.models.run import (
    Artifact,
    CodeValidation,
    PostProcessing,
    PreparingSample,
    PromptExecution,
    ResponseParsing,
    Run,
    Sample,
)
from mc_bench.util.object_store import get_client
from mc_bench.util.postgres import managed_session
from mc_bench.util.text import parse_known_parts

from ..app import app
from ..config import settings

HERE = os.path.dirname(os.path.abspath(__file__))
ADMIN_WORKER_DIR = os.path.dirname(HERE)
ESLINT_CONFIG = os.path.join(ADMIN_WORKER_DIR, "script-eslintrc.js")
MOCK_SCRIPT = os.path.join(ADMIN_WORKER_DIR, "js_scripts", "mockScript.js")


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
            "comparison_correlation_id": run.generate_correlation_id(),
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


@app.task(name="run.parse_prompt", bind=True)
def parse_prompt(
    self,
    sample_id,
):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        run_id = run.id
        run_external_id = run.external_id
        num_samples = len(run.samples)
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
            if num_samples < 5:
                admin_api_client = Client(token=self.request.headers["token"])
                admin_api_client.start_run_over(run_external_id)

            else:
                emit_event(RunStateChanged(run_id=run_id, new_state=RUN_STATE.FAILED))

            raise RuntimeError("Prompting didn't go well")

        return sample_id


@app.task(name="run.code_validation", bind=True)
def code_validation(self, sample_id):
    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        run_id = run.id
        num_samples = len(run.samples)
        run_external_id = run.external_id
        run_stage = db.scalar(
            select(CodeValidation).where(PostProcessing.run_id == run.id)
        )
        run_stage_id = run_stage.id
        code = sample.result_code_text

    with tempfile.TemporaryDirectory() as temp_dir:
        with open(MOCK_SCRIPT, "r") as f:
            mock_script = f.read()

        with open(os.path.join(temp_dir, "code.js"), "w") as f:
            full_code = f"{mock_script}\n\n{code}"
            f.write(full_code)

        result = subprocess.run(
            ["eslint", "--config", ESLINT_CONFIG, "code.js"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            print("Code validation failed. Reprompting...")
            if num_samples < 5:
                admin_api_client = Client(token=self.request.headers["token"])
                admin_api_client.start_run_over(run_external_id)

            else:
                emit_event(RunStateChanged(run_id=run_id, new_state=RUN_STATE.FAILED))

            emit_event(
                RunStageStateChanged(
                    stage_id=run_stage_id, new_state=RUN_STAGE_STATE.FAILED
                )
            )
            raise RuntimeError("Code validation failed. Reprompting...")

        else:
            emit_event(
                RunStageStateChanged(
                    stage_id=run_stage_id, new_state=RUN_STAGE_STATE.COMPLETED
                )
            )
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
        run_id = run.id
        run_stage = db.scalar(
            select(PreparingSample).where(PreparingSample.run_id == run.id)
        )

        run_stage_id = run_stage.id
        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.IN_PROGRESS
            )
        )

        artifact = sample.get_render_artifact()
        if not artifact:
            raise RuntimeError("No render artifact found")

        object_client = get_client()

        render_artifact_spec = sample.comparison_artifact_spec(db)
        for key in ["rendered_model_glb"]:
            with tempfile.TemporaryDirectory() as tmp_dir:
                artifact_bytes = artifact.download_artifact()
                with open(os.path.join(tmp_dir, "artifact.glb"), "wb") as f:
                    f.write(artifact_bytes.getvalue())

                object_client.fput_object(
                    bucket_name=settings.EXTERNAL_OBJECT_BUCKET,
                    object_name=render_artifact_spec[key]["object_prototype"]
                    .materialize(**render_artifact_spec[key]["object_parts"])
                    .get_path(),
                    file_path=os.path.join(tmp_dir, "artifact.glb"),
                )

        for key, spec in render_artifact_spec.items():
            artifact = Artifact(
                kind=spec["artifact_kind"],
                run_id=run_id,
                sample_id=sample_id,
                bucket=settings.EXTERNAL_OBJECT_BUCKET,
                key=spec["object_prototype"]
                .materialize(**spec["object_parts"])
                .get_path(),
            )
            db.add(artifact)
        db.commit()

        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.COMPLETED
            )
        )
        emit_event(RunStateChanged(run_id=run_id, new_state=RUN_STATE.COMPLETED))
        return sample_id
