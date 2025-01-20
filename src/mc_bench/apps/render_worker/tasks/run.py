import os
import tempfile

from mc_bench.minecraft.rendering import Renderer
from mc_bench.minecraft.resources import ResourceLoader
from mc_bench.minecraft.schematic import load_schematic, to_placed_blocks
from mc_bench.models.run import Artifact, RenderingSample
from mc_bench.util.object_store import get_client as get_object_store_client
from mc_bench.worker.run_stage import StageContext, run_stage_task

from ..app import app
from ..config import settings


@run_stage_task(
    name="run.render_sample",
    app=app,
    max_retries=0,
    stage=RenderingSample,
    retry_on_failure=False,
    restart_run_on_failure=False,
)
def render_sample(stage_context: StageContext):
    resource_loader = ResourceLoader(
        version=stage_context.run.template.minecraft_version,
    )

    schematic_artifact = stage_context.sample.get_schematic_artifact()

    with tempfile.TemporaryDirectory() as temp_dir:
        schematic_filepath = os.path.join(temp_dir, "build.schem")
        rendered_model_glb_filepath = os.path.join(temp_dir, "build-rendered-model.glb")
        with open(schematic_filepath, "wb") as f:
            f.write(schematic_artifact.download_artifact().getvalue())

        blocks = load_schematic(schematic_filepath)
        placed_blocks = to_placed_blocks(blocks, resource_loader)

        renderer = Renderer()
        renderer.convert_blocks_to_file(
            placed_blocks=placed_blocks, output_filepath=rendered_model_glb_filepath
        )

        object_client = get_object_store_client()

        render_artifact_spec = stage_context.sample.render_artifact_spec(
            stage_context.db
        )
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
                run_id=stage_context.run.id,
                sample_id=stage_context.sample.id,
                bucket=settings.INTERNAL_OBJECT_BUCKET,
                key=spec["object_prototype"]
                .materialize(**spec["object_parts"])
                .get_path(),
            )
            stage_context.db.add(artifact)
        stage_context.db.commit()

    run_id = stage_context.run_id
    sample_id = stage_context.sample.id

    return run_id, sample_id
