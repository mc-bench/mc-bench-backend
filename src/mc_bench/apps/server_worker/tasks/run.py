import json
import os
import time
from io import BytesIO

from sqlalchemy import select

from mc_bench.clients.mcbench_admin_api import Client
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
    RUN_STAGE_STATE,
    Artifact,
    Building,
    ExportingContent,
    Run,
    Sample,
    run_stage_state_id_for,
)
from mc_bench.util.object_store import get_client
from mc_bench.util.postgres import managed_session

from ..app import app
from ..config import settings
from ..templates import build_template, export_template

MINECRAFT_SERVER_IMAGE = os.environ["MINECRAFT_SERVER_IMAGE"]
MINECRAFT_BUILDER_IMAGE = os.environ["MINECRAFT_BUILDER_IMAGE"]


def error_handler(stage_class):
    def wrapper(self, exc, task_id, args, kwargs, einfo):
        if self.request.retries < self.max_retries:
            print(f"Task {task_id} is in retry, not marking as failed")
            return

        print(f"Task {task_id} failed: {exc}")

        sample_id = args[0] if args else kwargs.get("sample_id")

        with managed_session() as db:
            sample = db.scalar(select(Sample).where(Sample.id == sample_id))
            run = db.scalar(select(Run).where(Run.id == sample.run_id))
            sample_id = sample.id
            run_id = run.id
            run_stage = db.scalar(
                select(stage_class).where(stage_class.run_id == run_id)
            )

            run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.FAILED)
            db.add(run_stage)
            db.commit()

            run_stage.set_progress(0, note=None)

    return wrapper


def retry_handler(stage_class):
    def wrapper(self, exc, task_id, args, kwargs, einfo):
        print(f"Task {task_id} failed: {exc}")

        sample_id = args[0] if args else kwargs.get("sample_id")

        with managed_session() as db:
            sample = db.scalar(select(Sample).where(Sample.id == sample_id))
            run = db.scalar(select(Run).where(Run.id == sample.run_id))
            sample_id = sample.id
            run_id = run.id
            run_stage = db.scalar(
                select(stage_class).where(stage_class.run_id == run_id)
            )

            run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_RETRY)
            db.add(run_stage)
            db.commit()

    return wrapper


@app.task(
    name="run.build_structure",
    autoretry_for=(Exception,),
    on_failure=error_handler(Building),
    on_retry=retry_handler(Building),
    bind=True,
)
def build_structure(self, sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    admin_api_client = Client(
        token=self.request.headers["token"],
    )

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        code = sample.result_code_text
        sample_id = sample.id
        run_id = run.id
        run_external_id = run.external_id
        run_stage = db.scalar(select(Building).where(Building.run_id == run.id))

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS)
        db.add(run_stage)
        db.commit()

        suffix = f"{self.request.id}-{int(time.time())}"
        network_name = create_network(suffix)
        structure_name = f"sample_{sample_id}"

        file_spec = sample.build_artifact_spec(
            db=db,
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
        admin_api_client.update_stage_progress(
            run_external_id=run_external_id,
            stage="BUILDING",
            progress=0,
            note="starting ephemeral minecraft server",
        )

        server = start_server(MINECRAFT_SERVER_IMAGE, network_name, suffix)
        server_id = server.id

        wait_for_server(server_id)

        admin_api_client.update_stage_progress(
            run_external_id=run_external_id,
            stage="BUILDING",
            progress=0,
            note="starting the build",
        )

        builder = run_builder(
            image=MINECRAFT_BUILDER_IMAGE,
            network_name=network_name,
            server_container_id=server_id,
            suffix=suffix,
            build_script_volume=volume,
            structure_name=structure_name,
        )
        builder_id = builder.id

        build_command_count = 0

        for log_index, log_line in enumerate(server.logs(stream=True)):
            decoded_log_line = log_line.decode("utf-8")
            print(decoded_log_line)

            if "/setblock" in decoded_log_line or "/fill" in decoded_log_line:
                build_command_count += 1

            # when we break out of this the container will be done
            if build_command_count % 50 == 0:
                admin_api_client.update_stage_progress(
                    run_external_id=run_external_id,
                    stage="BUILDING",
                    progress=0,
                    note=f"building... ({build_command_count} build commands executed)",
                )

            if (
                "builder left the game" in decoded_log_line
                and builder.status != "running"
            ):
                break

        admin_api_client.update_stage_progress(
            run_external_id=run_external_id,
            stage="BUILDING",
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

    with managed_session() as db:
        for file_key, spec in file_spec.items():
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

        run_stage = db.scalar(select(Building).where(Building.run_id == run_id))

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)
        db.add(run_stage)
        db.commit()

        return sample_id


@app.task(
    bind=True,
    name="run.export_structure_views",
    autoretry_for=(Exception,),
    on_failure=error_handler(ExportingContent),
    on_retry=retry_handler(ExportingContent),
)
def export_structure_views(self, sample_id):
    admin_api_client = Client(
        token=self.request.headers["token"],
    )

    if sample_id is None:
        raise RuntimeError("sample_id is required")

    time.sleep(15)

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        sample_id = sample.id
        run_id = run.id
        run_external_id = run.external_id
        command_list_artifact = sample.get_command_list_artifact()
        summary_artifact = sample.get_build_summary_artifact()
        run_stage = db.scalar(
            select(ExportingContent).where(ExportingContent.run_id == run_id)
        )

        structure_name = f"sample_{sample_id}"

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.IN_PROGRESS)
        db.add(run_stage)
        db.commit()

        command_list = json.loads(
            command_list_artifact.download_artifact().getvalue().decode("utf-8")
        )

        file_spec = sample.export_artifact_spec(db, structure_name)

        admin_api_client.update_stage_progress(
            run_external_id=run_external_id,
            stage="EXPORTING_CONTENT",
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

    suffix = f"{self.request.id}-{int(time.time())}"
    network_name = create_network(suffix)

    volume = create_volume(export_script)

    # set here in case we fail in the try/except below before they get set
    builder_id = None
    server_id = None

    try:
        admin_api_client.update_stage_progress(
            run_external_id=run_external_id,
            stage="EXPORTING_CONTENT",
            progress=0,
            note="starting ephemeral minecraft server",
        )

        server = start_server(MINECRAFT_SERVER_IMAGE, network_name, suffix)
        server_id = server.id
        progress = 0.0

        wait_for_server(server_id)

        admin_api_client.update_stage_progress(
            run_external_id=run_external_id,
            stage="EXPORTING_CONTENT",
            progress=progress,
            note="starting build",
        )

        builder = run_builder(
            image=MINECRAFT_BUILDER_IMAGE,
            network_name=network_name,
            server_container_id=server_id,
            suffix=suffix,
            build_script_volume=volume,
            structure_name=structure_name,
        )
        builder_id = builder.id

        last_retrieved_time = time.monotonic()
        expected_frame_count = calculate_expected_frames(
            command_list=command_list,
        )

        print(f"Expected frame count: {expected_frame_count}")

        for log_line in builder.logs(stream=True):
            if time.monotonic() - last_retrieved_time > 20:
                last_retrieved_time = time.monotonic()
                frame_count_data = get_file_from_container(
                    builder_id, file_path="/data/frame_count.txt"
                )
                if frame_count_data:
                    frame_count = int(frame_count_data.strip())
                    progress = frame_count / expected_frame_count
                    admin_api_client.update_stage_progress(
                        run_external_id=run_external_id,
                        stage="EXPORTING_CONTENT",
                        progress=progress,
                        note=f"exporting cinematic frames (~{frame_count}/{expected_frame_count})",
                    )

            # when we break out of this the container will be done
            print(log_line.decode("utf-8"))

        admin_api_client.update_stage_progress(
            run_external_id=run_external_id,
            stage="EXPORTING_CONTENT",
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

    with managed_session() as db:
        for key, spec in file_spec.items():
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

        run_stage = db.scalar(
            select(ExportingContent).where(ExportingContent.run_id == run_id)
        )

        run_stage.state_id = run_stage_state_id_for(db, RUN_STAGE_STATE.COMPLETED)
        db.add(run_stage)
        db.commit()

        return sample_id
