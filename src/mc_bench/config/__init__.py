import json
import os


class CeleryConfig:
    @property
    def broker_url(self):
        return os.environ["CELERY_BROKER_URL"]


class PostgresConfig:
    @property
    def host(self):
        return os.environ["POSTGRES_HOST"]

    @property
    def database(self):
        return os.environ["POSTGRES_DATABASE"]

    @property
    def user(self):
        return os.environ["POSTGRES_USER"]

    @property
    def password(self):
        return os.environ["POSTGRES_PASSWORD"]

    @property
    def port(self):
        return int(os.environ["POSTGRES_PORT"])

    @property
    def options(self):
        return json.loads(os.environ.get("POSTGRES_OPTIONS", "{}"))
