from mc_bench.util.celery import make_worker_celery_app

app = make_worker_celery_app(
    conf=dict(
        worker_prefetch_multiplier=4,
    )
)
