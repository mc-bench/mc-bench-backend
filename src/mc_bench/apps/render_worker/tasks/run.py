import os
import tempfile

from sqlalchemy import select

from mc_bench.constants import RUN_STAGE_STATE, RUN_STATE
from mc_bench.events import emit_event
from mc_bench.events.types import RunStageStateChanged, RunStateChanged
from mc_bench.minecraft.rendering import Renderer
from mc_bench.minecraft.resources import ResourceLoader
from mc_bench.minecraft.schematic import load_schematic, to_placed_blocks
from mc_bench.models.run import Artifact, RenderingSample, Run, Sample
from mc_bench.util.object_store import get_client as get_object_store_client
from mc_bench.util.postgres import managed_session

from ..app import app
from ..config import settings


@app.task(name="run.render_sample")
def render_sample(sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        minecraft_version = run.template.minecraft_version
        run_id = run.id
        run_stage = db.scalar(
            select(RenderingSample).where(RenderingSample.run_id == run.id)
        )

        run_stage_id = run_stage.id
        emit_event(
            RunStageStateChanged(
                stage_id=run_stage_id, new_state=RUN_STAGE_STATE.IN_PROGRESS
            )
        )

        resource_loader = ResourceLoader(
            version=minecraft_version,
        )
        schematic_artifact = sample.get_schematic_artifact()

        with tempfile.TemporaryDirectory() as temp_dir:
            schematic_filepath = os.path.join(temp_dir, "build.schem")
            rendered_model_glb_filepath = os.path.join(
                temp_dir, "build-rendered-model.glb"
            )
            with open(schematic_filepath, "wb") as f:
                f.write(schematic_artifact.download_artifact().getvalue())

            blocks = load_schematic(schematic_filepath)
            placed_blocks = to_placed_blocks(blocks, resource_loader)

            renderer = Renderer()
            renderer.convert_blocks_to_file(
                placed_blocks=placed_blocks, output_filepath=rendered_model_glb_filepath
            )

            object_client = get_object_store_client()

            render_artifact_spec = sample.render_artifact_spec(db)
            for key in ["rendered_model_glb"]:
                object_client.fput_object(
                    bucket_name=settings.INTERNAL_OBJECT_BUCKET,
                    object_name=render_artifact_spec[key]["object_prototype"]
                    .materialize(**render_artifact_spec[key]["object_parts"])
                    .get_path(),
                    file_path=rendered_model_glb_filepath,
                )

            for key, spec in render_artifact_spec.items():
                artifact = Artifact(
                    kind=spec["artifact_kind"],
                    run_id=run_id,
                    sample_id=sample_id,
                    bucket=settings.INTERNAL_OBJECT_BUCKET,
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
        return sample_id
