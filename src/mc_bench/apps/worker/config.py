import logging
import os


class Settings:
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"
    LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO")
    LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)

    # ELO calculation settings
    ELO_BATCH_SIZE = int(os.environ.get("ELO_BATCH_SIZE", "1000"))
    ELO_K_FACTOR = float(os.environ.get("ELO_K_FACTOR", "32.0"))
    ELO_DEFAULT_SCORE = float(os.environ.get("ELO_DEFAULT_SCORE", "1000.0"))
    ELO_MIN_SCORE = float(os.environ.get("ELO_MIN_SCORE", "100.0"))


settings = Settings()
