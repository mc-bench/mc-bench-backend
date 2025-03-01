import os

from celery import Celery, signals

DEFAULT_WORKER_CONF = dict(
    # For now let's limit tasks to 24 hours
    task_time_limit=86400,
    task_soft_time_limit=82800,
    # Same as task_time_limit
    worker_send_task_events=True,
    # Broker settings to help with worker reliability
    broker_heartbeat=300,
    broker_connection_timeout=30,
    # Our tasks are technically idempotent, but we want to avoid multiple executions
    task_acks_late=False,
    # worker_lost might occur during redeploys and that kind of thing
    task_reject_on_worker_lost=True,
    # We want to avoid stale results
    result_expires=172800,
    # We want to make sure to spread load tasks across all workers
    worker_prefetch_multiplier=1,
    # experimental to maybe avoid memory leaks
    worker_max_tasks_per_child=16,
    # We want to make sure to retry connection to the broker on startup
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
)

DEFAULT_CLIENT_CONF = dict()


@signals.setup_logging.connect
def on_setup_logging(**kwargs):
    pass


def make_worker_celery_app(conf=None):
    conf = conf or {}
    app = Celery(
        broker=os.environ["CELERY_BROKER_URL"],
        backend=os.environ["CELERY_BROKER_URL"],
    )

    conf_update = dict(DEFAULT_WORKER_CONF)
    conf_update.update(conf)
    app.conf.update(conf_update)
    return app


def make_client_celery_app(conf=None):
    conf = conf or {}
    app = Celery(
        broker=os.environ["CELERY_BROKER_URL"],
        backend=os.environ["CELERY_BROKER_URL"],
    )

    conf_update = dict(DEFAULT_CLIENT_CONF)
    conf_update.update(conf)
    app.conf.update(conf_update)
    return app
