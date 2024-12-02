import datetime
import os
import time

from sqlalchemy import select

from mc_bench.minecraft.server import (
    cleanup,
    copy_from_container,
    create_network,
    run_builder,
    start_server,
    wait_for_server,
)
from mc_bench.models.run import (
    RUN_STATE,
    Artifact,
    ArtifactKind,
    Run,
    Sample,
    run_state_id_for,
)
from mc_bench.schema.object_store.runs import KINDS, runs
from mc_bench.util.object_store import get_client
from mc_bench.util.postgres import managed_session

from ..app import app
from ..config import settings
from ..template import template


@app.task(name="run.build_structure")
def build_structure(sample_id):
    if sample_id is None:
        raise RuntimeError("sample_id is required")

    time.sleep(15)

    with managed_session() as db:
        sample = db.scalar(select(Sample).where(Sample.id == sample_id))
        run = db.scalar(select(Run).where(Run.id == sample.run_id))
        code = sample.result_code_text
        sample_id = sample.id
        run_id = run.id

    suffix = f"{sample_id}-{int(time.time())}"
    network_name = create_network(suffix)
    structure_name = f"sample_{sample_id}"
    server_id = None

    try:
        server_id = start_server(network_name, suffix)

        if wait_for_server(server_id):
            output = run_builder(
                network_name=network_name,
                server_container_id=server_id,
                suffix=suffix,
                script=template.replace("REPLACE_ME", code),
                structure_name=structure_name,
            )
            print("Builder output:", output)
        else:
            raise RuntimeError("Server failed to start within timeout period")

        host_path_directory = f"/data/schematics/{sample_id}/"
        host_path_filename = f"/data/schematics/{sample_id}/{structure_name}.schem"

        copy_from_container(
            container_name=server_id,
            container_path=os.path.join(
                "/data/plugins/WorldEdit/schematics", f"{structure_name}.schem"
            ),
            host_path=host_path_directory,
        )

    finally:
        pass
        if server_id is not None:
            cleanup(network_name, server_id)

    object_client = get_client()
    schematic_file = runs.get(
        KINDS.RUN,
        KINDS.SAMPLE,
        KINDS.ARTIFACTS,
        KINDS.BUILD_SCHEMATIC,
    ).materialize(
        run_id=run_id,
        sample_id=sample_id,
        name=f'{run_id}_{sample_id}_{datetime.datetime.now().isoformat().replace(":", "_")}',
    )

    object_client.fput_object(
        bucket_name=settings.INTERNAL_OBJECT_BUCKET,
        object_name=schematic_file.get_path(),
        file_path=host_path_filename,
    )

    with managed_session() as db:
        run.state_id = run_state_id_for(db, RUN_STATE.BUILD_COMPLETED)
        artifact_kind = db.scalar(
            select(ArtifactKind).where(ArtifactKind.name == "BUILD_SCHEMATIC")
        )
        artifact = Artifact(
            kind=artifact_kind,
            run_id=run_id,
            sample_id=sample_id,
            bucket=settings.INTERNAL_OBJECT_BUCKET,
            key=schematic_file.get_path(),
        )
        db.add(artifact)
        db.commit()

        run.state_id = run_state_id_for(db, RUN_STATE.POST_PROCESSING_ENQUEUED)
        db.commit()

        return sample_id
