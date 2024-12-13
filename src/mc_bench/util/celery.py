import os

from celery import Celery

from dotenv import load_dotenv

load_dotenv()


def make_celery_app():
    return Celery(
        broker=os.environ["CELERY_BROKER_URL"],
        backend=os.environ["CELERY_BROKER_URL"],
    )
