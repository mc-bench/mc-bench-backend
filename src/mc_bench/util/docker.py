import queue
import threading

import docker


class ContainerStopped:
    def __init__(self, status):
        self._status = status

    def errored(self):
        return self._status["StatusCode"] != 0

    @property
    def status_code(self):
        return self._status["StatusCode"]


class LogItem:
    def __init__(self, container_id, log_line):
        self.container_id = container_id
        self.log_line = log_line


def watch_container(queue, container_id):
    docker_client = docker.from_env()
    container = docker_client.containers.get(container_id)
    queue.put(ContainerStopped(container.wait()))


def stream_logs(queue, container_id):
    docker_client = docker.from_env()
    container = docker_client.containers.get(container_id)
    for log_line in container.logs(stream=True):
        queue.put((container_id, log_line))


def wait_for_containers(container_ids):
    item_queue = queue.Queue()

    for container_id in container_ids:
        for target in [watch_container, stream_logs]:
            thread = threading.Thread(
                target=target, args=(item_queue, container_id), daemon=True
            )
            thread.start()

    while True:
        queue_item = item_queue.get()
        if isinstance(queue_item, ContainerStopped):
            if queue_item.errored():
                raise RuntimeError(
                    f"{container_id} container exited with non-zero status: {queue_item.status_code}"
                )
            else:
                break
        else:
            yield LogItem(queue_item[0], queue_item[1])
