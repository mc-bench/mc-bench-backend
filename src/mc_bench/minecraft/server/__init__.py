import io
import os
import re
import tarfile
import time
from typing import Dict, Optional, Union

import docker
import docker.models.containers
import docker.models.volumes

from mc_bench.util.logging import get_logger

logger = get_logger(__name__)


def create_network(suffix, exists_ok=False) -> str:
    """Create a new overlay network and return its name."""
    client = docker.from_env()
    network_name = f"mctest-net-{suffix}"
    try:
        logger.debug(
            "Checking if network exists", network_name=network_name
        )  # Changed to debug - implementation detail
        client.networks.get(network_name)
        if not exists_ok:
            raise ValueError(f"Network {network_name} already exists")
    except docker.errors.NotFound:
        logger.info(
            "Network does not exist, creating it", network_name=network_name
        )  # Keep as info - important state change
        client.networks.create(network_name, driver="bridge", check_duplicate=True)
        logger.info(
            "Network created", network_name=network_name
        )  # Keep as info - important state change
    return network_name


def start_server(image, network_name: str, suffix, ports=None, replace=False) -> str:
    """Start the Minecraft server container and return its container ID."""
    client = docker.from_env()
    kwargs = {}

    if ports:
        kwargs["ports"] = ports

    if not os.environ.get("NO_IMAGE_PULL"):
        client.images.pull(image)

    container_name = f"mc-server-{suffix}"

    try:
        logger.debug(
            "Getting existing container", container_name=container_name
        )  # Changed to debug - implementation detail
        current_container = client.containers.get(container_name)
    except docker.errors.NotFound:
        logger.debug(
            "Container not found", container_name=container_name
        )  # Changed to debug - implementation detail
        current_container = None

    if current_container is not None:
        if replace:
            logger.info(
                "Stopping existing container", container_name=container_name
            )  # Keep as info - important state change
            current_container.stop()
            logger.info(
                "Removing existing container", container_name=container_name
            )  # Keep as info - important state change
            current_container.remove()
            logger.info(
                "Container removed", container_name=container_name
            )  # Keep as info - important state change
        else:
            raise ValueError(f"Container {container_name} already exists")

    logger.info("Creating new container", container_name=container_name)
    container = client.containers.run(
        image,
        detach=True,
        remove=False,
        network=network_name,
        name=container_name,
        **kwargs,
    )

    logger.info("Container created", container_name=container_name)
    return container


def wait_for_server(container_id: str, timeout: int = 300) -> bool:
    """
    Wait for the Minecraft server to be ready by checking for the standard
    server startup completion message: "Done (Xs)!"

    Args:
        container_id: Docker container ID running the Minecraft server
        timeout: Maximum time to wait in seconds (default: 300)

    Returns:
        bool: True if server is ready, False if timeout reached
    """
    client = docker.from_env()
    logger.debug(
        "Getting container", container_id=container_id
    )  # Changed to debug - implementation detail
    container = client.containers.get(container_id)
    start_time = time.time()

    # Regex pattern to match Minecraft server ready message
    # Matches strings like "Done (1.234s)!" or "Done (12.4s)!"
    ready_pattern = re.compile(r"Done \(\d+\.?\d*s\)!")

    while time.time() - start_time < timeout:
        logs = container.logs().decode("utf-8")
        if ready_pattern.search(logs):
            logger.info("Server is ready", container_id=container_id)
            return True
        time.sleep(2)

    return False


def run_builder(
    image,
    network_name: str,
    server_container_id: str,
    suffix: str,
    build_script_volume: docker.models.volumes.Volume,
    structure_name,
    env: Optional[Dict[str, str]] = None,
    **kwargs,
) -> docker.models.containers.Container:
    env = env or {}

    client = docker.from_env()
    server_container = client.containers.get(server_container_id)

    if not os.environ.get("NO_IMAGE_PULL"):
        logger.info("Pulling image", image=image)  # Keep as info - important operation
        client.images.pull(image)

    logger.info(
        "Running builder", image=image, network_name=network_name, suffix=suffix
    )  # Keep as info - important operation
    builder = client.containers.run(
        image,
        environment={
            "HOST": server_container.name,
            "PORT": "25565",
            "DELAY": "75",
            "STRUCTURE_NAME": structure_name,
            "OUTDIR": "/data",
            **env,
        },
        network=network_name,
        remove=False,
        detach=True,
        volumes={build_script_volume.name: {"bind": "/build-scripts", "mode": "ro"}},
        name=f"mc-builder-{suffix}",
        **kwargs,
    )
    logger.info("Builder running", builder=builder)
    return builder


def cleanup(
    network_name: str,
    server_container_id: Optional[str],
    build_container_id: Optional[str],
    volume: docker.models.volumes.Volume,
):
    """Clean up resources after we're done."""
    logger.info("Cleaning up docker resources after minecraft server run")
    client = docker.from_env()

    # Stop and remove the server container
    try:
        if (
            server_container_id is not None
            and not os.environ.get("NO_CLEANUP_SERVER_CONTAINER") == "true"
        ):
            logger.info(
                "Stopping server container", server_container_id=server_container_id
            )
            container = client.containers.get(server_container_id)
            container.stop()
            container.remove()

    except docker.errors.NotFound:
        logger.info(
            "Server container not found", server_container_id=server_container_id
        )
        pass

    try:
        if (
            build_container_id is not None
            and not os.environ.get("NO_CLEANUP_BUILDER_CONTAINER") == "true"
        ):
            logger.info(
                "Stopping builder container", build_container_id=build_container_id
            )
            container = client.containers.get(build_container_id)
            container.stop()
            container.remove()

    except docker.errors.NotFound:
        logger.info(
            "Builder container not found", build_container_id=build_container_id
        )
        pass

    try:
        if (
            not os.environ.get("NO_CLEANUP_SERVER_CONTAINER") == "true"
            and not os.environ.get("NO_CLEANUP_BUILDER_CONTAINER") == "true"
        ):
            logger.info("Removing network", network_name=network_name)
            network = client.networks.get(network_name)
            network.remove()
    except docker.errors.NotFound:
        logger.info("Network not found", network_name=network_name)
        pass

    try:
        if not os.environ.get("NO_CLEANUP_BUILDER_CONTAINER") == "true":
            logger.info("Removing volume", volume=volume)
            volume.remove(force=True)
    except Exception:
        logger.info("Volume not found", volume=volume)
        pass


def copy_from_container(container_name, container_path, host_path):
    """
    Copy a file or directory from a Docker container to the host.

    Args:
        container_name (str): Name or ID of the container
        container_path (str): Path to the file/directory in the container
        host_path (str): Destination path on the host
    """
    # Initialize Docker client
    client = docker.from_env()
    logger.info(
        "Copying from container",
        container_name=container_name,
        container_path=container_path,
        host_path=host_path,
    )

    try:
        logger.info("Getting container", container_name=container_name)
        # Get container object
        container = client.containers.get(container_name)

        logger.info(
            "Getting file/directory from container", container_path=container_path
        )
        # Get file/directory from container
        bits, stat = container.get_archive(container_path)

        # Create a temporary tar file
        file_obj = io.BytesIO()
        for chunk in bits:
            file_obj.write(chunk)
        file_obj.seek(0)

        # Extract the tar archive
        with tarfile.open(fileobj=file_obj) as tar:
            # Create the destination directory if it doesn't exist
            os.makedirs(host_path, exist_ok=True)

            # Extract all contents
            tar.extractall(path=host_path)

        logger.info(
            "Successfully copied", container_path=container_path, host_path=host_path
        )

    except docker.errors.NotFound:
        logger.error("Container not found", container_name=container_name)
    except docker.errors.APIError as e:
        logger.error("Error copying file", error=e)
    finally:
        client.close()


def create_volume(
    data: Union[str, bytes], path="/build-scripts"
) -> docker.models.volumes.Volume:
    """
    Create a Docker volume and populate it with the provided data.

    Args:
        data: Content to write to shared_file.txt in the volume.
             Can be string or bytes.

    Returns:
        The populated Docker volume
    """
    client = docker.from_env()

    # Create volume
    volume = client.volumes.create()
    logger.info("Volume created", volume=volume.name)

    # Prepare data for tar
    if isinstance(data, str):
        data_bytes = data.encode("utf-8")
    else:
        data_bytes = data

    # Create tar containing the data
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        tar_info = tarfile.TarInfo(name="build-script.js")
        tar_info.size = len(data_bytes)
        tar.addfile(tar_info, io.BytesIO(data_bytes))
    tar_buffer.seek(0)

    if not os.environ.get("NO_IMAGE_PULL"):
        client.images.pull("alpine")
    # Create temporary container to populate volume
    logger.info("Creating temporary container", volume=volume.name, path=path)
    container = client.containers.run(
        "alpine",
        command="tail -f /dev/null",
        volumes={volume.name: {"bind": path, "mode": "rw"}},
        detach=True,
    )

    try:
        container.put_archive(path, tar_buffer.getvalue())
    finally:
        logger.info("Stopping temporary container", container_name=container.name)
        container.stop()
        logger.info("Removing temporary container", container_name=container.name)
        container.remove()

    return volume


def calculate_expected_frames(command_list):
    total_commands = len(command_list)
    total_frames_for_commands = total_commands * 2
    total_rotation_frames = 960

    return total_frames_for_commands + total_rotation_frames


def get_file_from_container(
    container_id: str, file_path: str, missing_ok=True, decode=True
) -> str:
    """
    Extract the contents of a file from a running Docker container.

    Args:
        container_id (str): The ID or name of the container
        file_path (str): The path to the file inside the container

    Returns:
        str: The contents of the file

    Raises:
        docker.errors.NotFound: If the container or file doesn't exist
        docker.errors.APIError: If there's an error communicating with Docker
    """
    # Initialize Docker client
    client = docker.from_env()
    logger.info(
        "Getting file from container", container_id=container_id, file_path=file_path
    )
    try:
        # Get container object
        container = client.containers.get(container_id)

        # Get file contents using container.get_archive()
        # This returns a tuple of (tar_data_stream, file_stats)
        tar_stream, _ = container.get_archive(file_path)

        # Import tarfile to handle the archive
        import io
        import tarfile

        # Create a BytesIO object from the tar stream
        tar_bytes = io.BytesIO()
        for chunk in tar_stream:
            tar_bytes.write(chunk)
        tar_bytes.seek(0)

        # Open the tar archive
        with tarfile.open(fileobj=tar_bytes) as tar:
            # Get the file from the archive
            file_obj = tar.extractfile(tar.getmembers()[0])
            if file_obj is None:
                raise ValueError(f"Could not read file {file_path}")

            if decode:
                # Read and decode the contents
                contents = file_obj.read().decode("utf-8")
            else:
                contents = file_obj.read()

        return contents

    except docker.errors.NotFound:
        if not missing_ok:
            logger.error("Container not found", container_id=container_id)
            raise ValueError(f"Container {container_id} not found")
        else:
            logger.info("Container not found", container_id=container_id)
            return None
    except Exception as e:
        logger.error("Error extracting file", error=e)
        raise Exception(f"Error extracting file: {str(e)}")
