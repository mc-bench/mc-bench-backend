from mc_bench.util.celery import make_client_celery_app

celery = make_client_celery_app()


def send_task(name, *args, **kwargs):
    kwargs.setdefault("queue", "admin")
    return celery.send_task(name, *args, **kwargs)


def create_runs(
    generation_id, prompt_ids, model_ids, template_ids, num_samples, progress_token
):
    return send_task(
        "generation.create_runs",
        kwargs=dict(
            generation_id=generation_id,
            prompt_ids=prompt_ids,
            model_ids=model_ids,
            template_ids=template_ids,
            num_samples=num_samples,
        ),
        headers={"token": progress_token},
    )
