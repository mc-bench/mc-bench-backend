from mc_bench.util.celery import make_celery_app

celery = make_celery_app()


def send_task(name, *args, **kwargs):
    kwargs.setdefault("queue", "default")
    return celery.send_task(name, *args, **kwargs)
