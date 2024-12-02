import argparse
import datetime
import os.path

import docker

HERE = os.path.dirname(os.path.abspath(__file__))


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry", type=str, default="registry.digitalocean.com/mcbench"
    )
    parser.add_argument("--repository", type=str, default="minecraft-server")
    parser.add_argument("--tag", type=str, default=datetime.date.today().isoformat())

    return parser


def get_image_tag(registry, repository, tag):
    return f"{registry}/{repository}:{tag}"


def build_image(tag):
    client = docker.from_env()
    image, logs = client.images.build(
        path=HERE, tag=tag, dockerfile="minecraft-server.Dockerfile"
    )
    for item in logs:
        if "stream" in item:
            print(item["stream"])
    return image


def run_image(tag):
    client = docker.from_env()
    return client.containers.run(tag, detach=True)


def main(options):
    tag = get_image_tag(
        options.registry,
        options.repository,
        options.tag,
    )

    image = build_image(tag)
    container = run_image(tag)

    logs = container.logs(stream=True)
    while True:
        logline = next(logs)
        print(logline.decode("utf-8").strip())
        if b"Timings Reset" in logline:
            break

    # wait until it's initialized
    exit_code, output = container.exec_run(["rcon-cli", "op", "builder"])
    if exit_code != 0:
        raise RuntimeError(output)

    print(output.decode("utf-8").strip())

    container.stop()
    container.commit(
        repository=f"{options.registry}/{options.repository}",
        tag=datetime.date.today().isoformat(),
    )
    return image, container


if __name__ == "__main__":
    parser = get_parser()
    options = parser.parse_args()
    main(options)
