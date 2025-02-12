import os


class Settings:
    INTERNAL_OBJECT_BUCKET = os.environ["INTERNAL_OBJECT_BUCKET"]
    EXTERNAL_OBJECT_BUCKET = os.environ["EXTERNAL_OBJECT_BUCKET"]
    FAST_RENDER = os.environ.get("FAST_RENDER") == "true"
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS") == "true"


settings = Settings()
