import logging
import os


class Settings:
    JWT_SECRET_KEY = os.environ["SECRET_KEY"]
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"
    LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO")
    LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)


settings = Settings()
