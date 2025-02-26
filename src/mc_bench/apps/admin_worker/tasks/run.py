import os
import subprocess
import tempfile

from mc_bench.constants import EXPERIMENTAL_STATE
from mc_bench.models.experimental_state import experimental_state_id_for
from mc_bench.models.run import (
    Artifact,
    CodeValidation,
    PostProcessing,
    PreparingSample,
    PromptExecution,
    ResponseParsing,
    Sample,
)
from mc_bench.util.logging import get_logger
from mc_bench.util.object_store import get_client
from mc_bench.util.text import parse_known_parts
from mc_bench.worker.run_stage import StageContext, run_stage_task

from ..app import app
from ..config import settings

logger = get_logger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
ADMIN_WORKER_DIR = os.path.dirname(HERE)
ESLINT_CONFIG = os.path.join(ADMIN_WORKER_DIR, "script-eslintrc.js")
MOCK_SCRIPT = os.path.join(ADMIN_WORKER_DIR, "js_scripts", "mockScript.js")


@run_stage_task(
    name="run.execute_prompt",
    app=app,
    stage=PromptExecution,
    max_retries=5,
    retry_backoff=5,
    retry_on_failure=True,
)
def execute_prompt(stage_context: StageContext):
    response = stage_context.run.model.default_provider.execute_prompt(
        prompt=stage_context.run.template.render(
            build_specification=stage_context.run.prompt.build_specification,
        )
    )

    sample_kwargs = {
        "created_by": stage_context.run.created_by,
        "run_id": stage_context.run.id,
        "raw": response,
        "comparison_correlation_id": stage_context.run.generate_correlation_id(),
    }

    experimental_states = [
        stage_context.run.template.experimental_state.name
        if stage_context.run.template.experimental_state
        else EXPERIMENTAL_STATE.EXPERIMENTAL.value,
        stage_context.run.model.experimental_state.name
        if stage_context.run.model.experimental_state
        else EXPERIMENTAL_STATE.EXPERIMENTAL.value,
        stage_context.run.prompt.experimental_state.name
        if stage_context.run.prompt.experimental_state
        else EXPERIMENTAL_STATE.EXPERIMENTAL.value,
    ]

    if all(
        [state == EXPERIMENTAL_STATE.RELEASED.value for state in experimental_states]
    ):
        sample_kwargs["experimental_state_id"] = experimental_state_id_for(
            stage_context.db, EXPERIMENTAL_STATE.RELEASED
        )
    else:
        sample_kwargs["experimental_state_id"] = experimental_state_id_for(
            stage_context.db, EXPERIMENTAL_STATE.EXPERIMENTAL
        )

    sample = Sample(**sample_kwargs)
    stage_context.db.add(sample)
    stage_context.db.commit()
    stage_context.db.refresh(sample)
    sample_id = sample.id

    run_id = stage_context.run_id

    return run_id, sample_id


@run_stage_task(
    name="run.parse_prompt",
    app=app,
    max_retries=0,
    stage=ResponseParsing,
    retry_on_failure=False,
    restart_run_on_failure=True,
)
def parse_prompt(
    stage_context: StageContext,
):
    parsed = parse_known_parts(stage_context.sample.raw)

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
            logger.info("num code lines", num_code_lines=len(code_lines))
            parsed["code"] = "\n".join(code_lines)

        stage_context.sample.result_code_text = parsed["code"].strip()

    if parsed.get("inspiration"):
        stage_context.sample.result_inspiration_text = parsed["inspiration"].strip()

    if parsed.get("description"):
        stage_context.sample.result_description_text = parsed["description"].strip()

    stage_context.db.commit()

    if not all(
        [
            parsed.get("code"),
            parsed.get("inspiration"),
            parsed.get("description"),
        ]
    ):
        logger.error("Prompting didn't go well", run_id=stage_context.run.id)
        raise RuntimeError("Prompting didn't go well")

    run_id = stage_context.run_id
    sample_id = stage_context.sample.id

    return run_id, sample_id


@run_stage_task(
    name="run.code_validation",
    app=app,
    max_retries=0,
    stage=CodeValidation,
    retry_on_failure=False,
    restart_run_on_failure=True,
)
def code_validation(stage_context: StageContext):
    code = stage_context.sample.result_code_text

    with tempfile.TemporaryDirectory() as temp_dir:
        with open(MOCK_SCRIPT, "r") as f:
            mock_script = f.read()

        with open(os.path.join(temp_dir, "code.js"), "w") as f:
            full_code = f"{mock_script}\n\n{code}"
            f.write(full_code)

        logger.info("Validating code", run_id=stage_context.run.id)
        result = subprocess.run(
            ["eslint", "--config", ESLINT_CONFIG, "code.js"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error("Code validation failed", run_id=stage_context.run.id)
            raise RuntimeError("Code validation failed.")

    run_id = stage_context.run_id
    sample_id = stage_context.sample.id

    return run_id, sample_id


@run_stage_task(
    name="run.post_processing",
    app=app,
    stage=PostProcessing,
    max_retries=0,
)
def post_process_build(stage_context: StageContext):
    run_id = stage_context.run_id
    sample_id = stage_context.sample.id

    return run_id, sample_id


@run_stage_task(
    name="run.prepare_sample",
    app=app,
    stage=PreparingSample,
    max_retries=1,
    terminal_stage=True,
)
def prepare_sample(stage_context: StageContext):
    artifact = stage_context.sample.get_render_artifact()

    if not artifact:
        logger.error("No render artifact found", run_id=stage_context.run.id)
        raise RuntimeError("No render artifact found")

    object_client = get_client()

    render_artifact_spec = stage_context.sample.comparison_artifact_spec(
        stage_context.db
    )

    for key in ["rendered_model_glb"]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact.download_contents_to_filepath(
                client=object_client,
                filepath=os.path.join(tmp_dir, "artifact.glb"),
            )

            object_key = (
                render_artifact_spec[key]["object_prototype"]
                .materialize(**render_artifact_spec[key]["object_parts"])
                .get_path()
            )

            sample_artifact = Artifact(
                kind=render_artifact_spec[key]["artifact_kind"],
                run_id=stage_context.run.id,
                sample_id=stage_context.sample.id,
                bucket=settings.EXTERNAL_OBJECT_BUCKET,
                key=object_key,
            )

            sample_artifact.upload_contents_from_filepath(
                client=object_client,
                filepath=os.path.join(tmp_dir, "artifact.glb"),
            )
            stage_context.db.add(sample_artifact)

    run_id = stage_context.run_id
    sample_id = stage_context.sample.id

    return run_id, sample_id
