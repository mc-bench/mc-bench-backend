import logging
import os


class Settings:
    INTERNAL_OBJECT_BUCKET = os.environ["INTERNAL_OBJECT_BUCKET"]
    EXPORT_STRUCTURE_VIEWS = os.environ.get("EXPORT_STRUCTURE_VIEWS", "true") == "true"
    EXPOSE_SERVER_PORTS = os.environ.get("EXPOSE_SERVER_PORTS", "false") == "true"
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"
    BUILD_DELAY = os.environ.get("BUILD_DELAY_MS", "25")
    LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO")
    LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)
    # Configure how frequently to log build commands at INFO level
    LOG_INTERVAL_COMMANDS = int(os.environ.get("LOG_INTERVAL_COMMANDS", "50"))
    # Configure how frequently to log export progress (as a percentage)
    LOG_INTERVAL_EXPORT_PERCENT = int(
        os.environ.get("LOG_INTERVAL_EXPORT_PERCENT", "10")
    )


settings = Settings()
