import os


class Settings:
    INTERNAL_OBJECT_BUCKET = os.environ["INTERNAL_OBJECT_BUCKET"]
    EXTERNAL_OBJECT_BUCKET = os.environ["EXTERNAL_OBJECT_BUCKET"]
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"


settings = Settings()
