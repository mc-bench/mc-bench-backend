import os


class Settings:
    INTERNAL_OBJECT_BUCKET = os.environ["INTERNAL_OBJECT_BUCKET"]
    EXPORT_STRUCTURE_VIEWS = os.environ.get("EXPORT_STRUCTURE_VIEWS", "true") == "true"
    EXPOSE_SERVER_PORTS = os.environ.get("EXPOSE_SERVER_PORTS", "false") == "true"
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"
    BUILD_DELAY = os.environ.get("BUILD_DELAY_MS", "25")


settings = Settings()
