import logging
import os


class Settings:
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"
    LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO")
    LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)


settings = Settings()
