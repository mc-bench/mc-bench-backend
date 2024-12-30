import argparse
import os

import mc_bench.minecraft.server
from mc_bench.minecraft.server import wait_for_server

SERVER_IMAGE = os.environ.get(
    "MINECRAFT_SERVER_IMAGE",
    "registry.digitalocean.com/mcbench/gameservers:minecraft-1.21.1-latest",
)


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=25565)
    parser.add_argument("--name", type=str, default="local-minecraft-server")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--version", type=str, default="1.21.1")
    return parser


def main(options):
    network = mc_bench.minecraft.server.create_network(options.name, exists_ok=True)

    result = mc_bench.minecraft.server.start_server(
        image=f"registry.digitalocean.com/mcbench/gameservers:minecraft-{options.version}-latest",
        network_name=network,
        suffix=options.name,
        ports={
            "25565/tcp": options.port,
        },
        replace=options.replace,
    )
    print("Waiting for server to start...")
    wait_for_server(result.id)
    print("Server started...")

    print(result)


if __name__ == "__main__":
    parser = get_parser()
    options = parser.parse_args()
    main(options)
