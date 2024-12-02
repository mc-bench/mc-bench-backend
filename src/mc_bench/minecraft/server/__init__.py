import io
import os
import tarfile
import time
from typing import Optional

import docker


def create_network(suffix) -> str:
    """Create a new overlay network and return its name."""
    client = docker.from_env()
    network_name = f"mctest-net-{suffix}"
    client.networks.create(network_name, driver="bridge", check_duplicate=True)
    return network_name


def start_server(network_name: str, suffix, ports=None) -> str:
    """Start the Minecraft server container and return its container ID."""
    client = docker.from_env()
    kwargs = {}

    if ports:
        kwargs["ports"] = ports

    container = client.containers.run(
        "registry.digitalocean.com/mcbench/minecraft-server:2024-12-01",
        detach=True,
        network=network_name,
        name=f"mc-server-{suffix}",
        **kwargs,
    )
    return container.id


def wait_for_server(container_id: str, timeout: int = 300) -> bool:
    """
    Wait for the server to be ready.
    Returns True if server is ready, False if timeout reached.

    Note: This is a placeholder implementation - you'll need to replace
    this with your actual readiness check logic.
    """
    client = docker.from_env()
    container = client.containers.get(container_id)
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Replace this with your actual readiness check
        # For example, you might want to:
        # - Check for specific log messages
        # - Try connecting to the server
        # - Check for a specific file creation
        logs = container.logs().decode("utf-8")
        if "Timings Reset" in logs:  # Replace with actual condition
            return True
        time.sleep(5)

    return False


def run_builder(
    network_name: str, server_container_id: str, suffix: str, script, structure_name
) -> Optional[str]:
    """
    Run the second container and return its output.
    Returns None if the server isn't ready.
    """
    client = docker.from_env()
    server_container = client.containers.get(server_container_id)

    # Run your second container
    container = client.containers.run(
        "registry.digitalocean.com/mcbench/minecraft-builder:2024-11-30",  # Replace with your actual image
        environment={
            "BUILD_SCRIPT": script,
            "HOST": server_container.name,
            "PORT": "25565",
            "DELAY": "75",
            "STRUCTURE_NAME": structure_name,
        },
        network=network_name,
        remove=True,  # Container will be removed after execution
    )

    return container.decode("utf-8")


def cleanup(network_name: str, server_container_id: str):
    """Clean up resources after we're done."""
    client = docker.from_env()

    # Stop and remove the server container
    try:
        container = client.containers.get(server_container_id)
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass

    # Remove the network
    try:
        network = client.networks.get(network_name)
        network.remove()
    except docker.errors.NotFound:
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

    try:
        # Get container object
        container = client.containers.get(container_name)

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

        print(f"Successfully copied {container_path} to {host_path}")

    except docker.errors.NotFound:
        print(f"Container {container_name} not found")
    except docker.errors.APIError as e:
        print(f"Error copying file: {e}")
    finally:
        client.close()
