import argparse
import os

import mc_bench.minecraft.server
from mc_bench.minecraft.server import wait_for_server

SERVER_IMAGE = os.environ.get(
    "MINECRAFT_SERVER_IMAGE", "registry.digitalocean.com/mcbench/minecraft-server:built"
)


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=25565)
    parser.add_argument("--name", type=str, default="local-minecraft-server")
    return parser


def main(options):
    network = mc_bench.minecraft.server.create_network(options.name)

    result = mc_bench.minecraft.server.start_server(
        image=SERVER_IMAGE,
        network_name=network,
        suffix=options.name,
        ports={
            "25565/tcp": options.port,
        },
    )
    print("Waiting for server to start...")
    wait_for_server(result)
    print("Server started...")

    print(result)


if __name__ == "__main__":
    parser = get_parser()
    options = parser.parse_args()
    main(options)
