import os

from redis import StrictRedis


class RedisDatabase:
    CELERY = 0
    CACHE = 1
    COMPARISON = 2


def get_redis_client(database, **kwargs) -> StrictRedis:
    kwargs["host"] = kwargs.get("host", os.environ.get("REDIS_HOST", "localhost"))
    kwargs["port"] = kwargs.get("port", os.environ.get("REDIS_PORT", 6379))

    kwargs["db"] = database

    if os.environ.get("REDIS_USE_AUTH", "true") == "true":
        kwargs["password"] = os.environ["REDIS_PASSWORD"]
        kwargs["username"] = os.environ["REDIS_USERNAME"]

    if os.environ.get("REDIS_USE_SSL", "true") == "true":
        kwargs["ssl"] = kwargs.pop("ssl", True)

    return StrictRedis(**kwargs)
