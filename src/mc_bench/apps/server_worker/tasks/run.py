import json
import os
import time
from io import BytesIO

from mc_bench.minecraft.server import (
    calculate_expected_frames,
    cleanup,
    copy_from_container,
    create_network,
    create_volume,
    get_file_from_container,
    run_builder,
    start_server,
    wait_for_server,
)
from mc_bench.models.run import (
    Artifact,
    Building,
    ExportingContent,
)
from mc_bench.util.docker import wait_for_containers
from mc_bench.util.logging import get_logger
from mc_bench.util.object_store import get_client
from mc_bench.worker.run_stage import StageContext, run_stage_task

from ..app import app
from ..config import settings
from ..templates import build_template, export_template

logger = get_logger(__name__)


def _get_server_image(minecraft_version: str) -> str:
    default_image = f"registry.digitalocean.com/mcbench/gameservers:minecraft-{minecraft_version}-latest"
    return os.environ.get("MINECRAFT_SERVER_IMAGE", default_image)


def _get_builder_image() -> str:
    return os.environ.get(
        "MINECRAFT_BUILDER_IMAGE",
        "registry.digitalocean.com/mcbench/minecraft-builder:1718738",
    )


@run_stage_task(
    name="run.build_structure",
    app=app,
    stage=Building,
    max_retries=0,
    retry_on_failure=False,
    restart_run_on_failure=True,
)
def build_structure(stage_context: StageContext):
    sample = stage_context.sample
    run = stage_context.run
    minecraft_version = run.template.minecraft_version
    code = sample.result_code_text
    sample_id = sample.id
    run_id = run.id

    suffix = f"{stage_context.task_id}-{int(time.time())}"
    network_name = create_network(suffix)
    structure_name = f"sample_{sample_id}"

    file_spec = sample.build_artifact_spec(
        db=stage_context.db,
        structure_name=structure_name,
    )

    build_script = build_template.replace(
        "async function buildCreation(startX, startY, startZ) {}", code
    )

    volume = create_volume(build_script)

    # set here in case we fail in the try/except below before they get set
    builder_id = None
    server_id = None

    try:
        stage_context.update_stage_progress(
            progress=0,
            note="starting ephemeral minecraft server",
        )

        server_args = dict(
            image=_get_server_image(minecraft_version),
            network_name=network_name,
            suffix=suffix,
        )

        if settings.EXPOSE_SERVER_PORTS:
            import random

            server_args["ports"] = {
                "25565/tcp": random.choice(range(26565, 27565 + 1000)),
            }

        server = start_server(**server_args)
        server_id = server.id

        wait_for_server(server_id)

        stage_context.update_stage_progress(
            progress=0,
            note="starting the build",
        )

        builder_args = dict(
            image=_get_builder_image(),
            network_name=network_name,
            server_container_id=server_id,
            suffix=suffix,
            build_script_volume=volume,
            structure_name=structure_name,
            env={
                "VERSION": minecraft_version,
                "DELAY": settings.BUILD_DELAY,
            },
        )

        builder = run_builder(**builder_args)
        builder_id = builder.id

        build_command_count = 0

        container_lookup = {
            builder_id: "builder",
            server_id: "server",
        }

        for log_item in wait_for_containers([builder_id, server_id]):
            container_id, log_line = log_item.container_id, log_item.log_line
            container_name = container_lookup[container_id]
            decoded_log_line = log_line.decode("utf-8")
            # Keep individual container logs at DEBUG level - very high cardinality
            logger.debug(f"{container_name}({container_id}): {decoded_log_line}")
            last_command_count_logged = build_command_count

            if container_name == "server":
                if "/setblock" in decoded_log_line or "/fill" in decoded_log_line:
                    build_command_count += 1

                if (
                    build_command_count != last_command_count_logged
                    and build_command_count > 1
                    and build_command_count % settings.LOG_INTERVAL_COMMANDS == 0
                ):
                    # Add INFO log with configurable interval
                    logger.info(
                        f"Build progress: {build_command_count} commands executed"
                    )
                    stage_context.update_stage_progress(
                        progress=0,
                        note=f"building... ({build_command_count} build commands executed)",
                    )
                    last_command_count_logged = build_command_count

        stage_context.update_stage_progress(
            progress=0.9,
            note="build complete, uploading artifacts",
        )

        for container_id, file_key in [
            (server_id, "schematic"),
            (builder_id, "command_list"),
            (builder_id, "build_summary"),
        ]:
            copy_from_container(
                container_name=container_id,
                container_path=file_spec[file_key]["container_path"],
                host_path=file_spec[file_key]["host_path_directory"],
            )
    finally:
        cleanup(network_name, server_id, builder_id, volume)

    object_client = get_client()

    for file_key in ["schematic", "command_list", "build_summary"]:
        object_client.fput_object(
            bucket_name=settings.INTERNAL_OBJECT_BUCKET,
            object_name=file_spec[file_key]["object_prototype"]
            .materialize(**file_spec[file_key]["object_parts"])
            .get_path(),
            file_path=os.path.join(
                file_spec[file_key]["host_path_directory"],
                file_spec[file_key]["host_file"],
            ),
        )

    object_client.put_object(
        bucket_name=settings.INTERNAL_OBJECT_BUCKET,
        object_name=file_spec["build_script"]["object_prototype"]
        .materialize(**file_spec["build_script"]["object_parts"])
        .get_path(),
        data=BytesIO(build_script.encode("utf-8")),
        length=len(build_script.encode("utf-8")),
    )

    for file_key, spec in file_spec.items():
        artifact = Artifact(
            kind=spec["artifact_kind"],
            run_id=run_id,
            sample_id=sample_id,
            bucket=settings.INTERNAL_OBJECT_BUCKET,
            key=spec["object_prototype"].materialize(**spec["object_parts"]).get_path(),
        )
        stage_context.db.add(artifact)
    stage_context.db.commit()

    return stage_context.run_id, stage_context.sample.id


@run_stage_task(
    name="run.export_structure_views",
    app=app,
    stage=ExportingContent,
    max_retries=0,
    retry_on_failure=False,
    restart_run_on_failure=False,
)
def export_structure_views(stage_context: StageContext):
    sample = stage_context.sample
    run = stage_context.run
    minecraft_version = run.template.minecraft_version
    sample_id = sample.id
    run_id = run.id
    command_list_artifact = sample.get_command_list_artifact()
    summary_artifact = sample.get_build_summary_artifact()

    structure_name = f"sample_{sample_id}"

    command_list = json.loads(
        command_list_artifact.download_artifact().getvalue().decode("utf-8")
    )

    file_spec = sample.export_artifact_spec(stage_context.db, structure_name)

    stage_context.update_stage_progress(
        progress=0,
        note="generating build script",
    )

    export_script = export_template.replace(
        "const summary = {}",
        f'const summary = {json.dumps(
            json.loads(
                summary_artifact.download_artifact().getvalue().decode("utf-8")
            )
        )}',
    ).replace(
        "const commandList = []", f"const commandList = {json.dumps(command_list)}"
    )

    if not settings.EXPORT_STRUCTURE_VIEWS:
        return stage_context.run_id, stage_context.sample_id

    suffix = f"{stage_context.task_id}-{int(time.time())}"
    network_name = create_network(suffix)

    volume = create_volume(export_script)

    # set here in case we fail in the try/except below before they get set
    builder_id = None
    server_id = None

    try:
        stage_context.update_stage_progress(
            progress=0,
            note="starting ephemeral minecraft server",
        )

        server_args = dict(
            image=_get_server_image(minecraft_version),
            network_name=network_name,
            suffix=suffix,
        )

        if settings.EXPOSE_SERVER_PORTS:
            import random

            server_args["ports"] = {
                "25565/tcp": random.choice(range(26565, 27565 + 1000)),
            }

        server = start_server(**server_args)
        server_id = server.id
        progress = 0.0

        wait_for_server(server_id)

        stage_context.update_stage_progress(
            progress=progress,
            note="starting build",
        )

        builder = run_builder(
            image=_get_builder_image(),
            network_name=network_name,
            server_container_id=server_id,
            suffix=suffix,
            build_script_volume=volume,
            structure_name=structure_name,
            env={"COMMANDS_PER_FRAME": str(get_frames_per_command(len(command_list)))},
        )
        builder_id = builder.id

        last_retrieved_time = time.monotonic()
        expected_frame_count = calculate_expected_frames(
            command_list=command_list,
        )

        logger.info(
            "Expected frame count", expected_frame_count=expected_frame_count
        )  # Keep as info - important configuration detail

        container_lookup = {
            builder_id: "builder",
            server_id: "server",
        }

        for log_item in wait_for_containers([builder_id, server_id]):
            container_id, log_line = log_item.container_id, log_item.log_line
            container_name = container_lookup[container_id]
            decoded_log_line = log_line.decode("utf-8")
            if time.monotonic() - last_retrieved_time > 20:
                last_retrieved_time = time.monotonic()
                frame_count_data = get_file_from_container(
                    builder_id, file_path="/data/frame_count.txt"
                )
                if frame_count_data:
                    frame_count = int(frame_count_data.strip())
                    progress = frame_count / expected_frame_count
                    stage_context.update_stage_progress(
                        progress=progress,
                        note=f"exporting cinematic frames (~{frame_count}/{expected_frame_count})",
                    )
                    # Add INFO log with frame count at configurable percentage intervals
                    interval_frames = (
                        expected_frame_count
                        * settings.LOG_INTERVAL_EXPORT_PERCENT
                        // 100
                    )
                    if interval_frames > 0 and frame_count % interval_frames == 0:
                        logger.info(
                            f"Export progress: {frame_count}/{expected_frame_count} frames ({progress:.1%})"
                        )

            # Keep individual container logs at DEBUG level - very high cardinality
            logger.debug(f"{container_name}({container_id}): {decoded_log_line}")

        stage_context.update_stage_progress(
            progress=progress,
            note="uploading content",
        )

        copy_from_container(
            container_name=builder.id,
            container_path=file_spec["timelapse"]["container_path"],
            host_path=file_spec["timelapse"]["host_path_directory"],
        )

        for side in ["north", "south", "east", "west"]:
            copy_from_container(
                container_name=builder.id,
                container_path=file_spec[f"{side}side_capture"]["container_path"],
                host_path=file_spec[f"{side}side_capture"]["host_path_directory"],
            )

    finally:
        cleanup(network_name, server_id, builder_id, volume)

    object_client = get_client()

    object_client.put_object(
        bucket_name=settings.INTERNAL_OBJECT_BUCKET,
        object_name=file_spec["command_list_build_script"]["object_prototype"]
        .materialize(**file_spec["command_list_build_script"]["object_parts"])
        .get_path(),
        data=BytesIO(export_script.encode("utf-8")),
        length=len(export_script.encode("utf-8")),
    )

    for key in [
        "northside_capture",
        "southside_capture",
        "eastside_capture",
        "westside_capture",
        "timelapse",
    ]:
        object_client.fput_object(
            bucket_name=settings.INTERNAL_OBJECT_BUCKET,
            object_name=file_spec[key]["object_prototype"]
            .materialize(**file_spec[key]["object_parts"])
            .get_path(),
            file_path=os.path.join(
                file_spec[key]["host_path_directory"],
                file_spec[key]["host_file"],
            ),
        )

    for key, spec in file_spec.items():
        artifact = Artifact(
            kind=spec["artifact_kind"],
            run_id=run_id,
            sample_id=sample_id,
            bucket=settings.INTERNAL_OBJECT_BUCKET,
            key=spec["object_prototype"].materialize(**spec["object_parts"]).get_path(),
        )
        stage_context.db.add(artifact)

    run_id = stage_context.run_id
    sample_id = stage_context.sample.id

    return run_id, sample_id


def get_frames_per_command(num_commands: int) -> int:
    return 10
    # return math.ceil(num_commands / 4500)
