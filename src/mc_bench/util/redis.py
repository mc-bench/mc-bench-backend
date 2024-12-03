import os
from functools import lru_cache

from redis import ConnectionPool, SSLConnection, StrictRedis


class RedisDatabase:
    CELERY = 0
    CACHE = 1
    COMPARISON = 2
    MINECRAFT_SERVER_REGISTRY = 3


@lru_cache
def get_redis_pool(database: int, **kwargs) -> ConnectionPool:
    kwargs["host"] = kwargs.get("host", os.environ.get("REDIS_HOST", "localhost"))
    kwargs["port"] = kwargs.get("port", os.environ.get("REDIS_PORT", 6379))

    kwargs["db"] = database

    if os.environ.get("REDIS_USE_AUTH", "true") == "true":
        kwargs["password"] = os.environ["REDIS_PASSWORD"]
        kwargs["username"] = os.environ["REDIS_USERNAME"]

    if os.environ.get("REDIS_USE_SSL", "true") == "true":
        kwargs["connection_class"] = SSLConnection
        kwargs["ssl_cert_reqs"] = "none"

    return ConnectionPool(**kwargs)


def get_redis_client(database: int = 0, **kwargs) -> StrictRedis:
    pool = get_redis_pool(database, **kwargs)
    return StrictRedis(connection_pool=pool)


def get_redis_database(database):
    def wrapper():
        redis = get_redis_client(database=database)
        try:
            yield redis
        finally:
            redis.close()

    return wrapper
