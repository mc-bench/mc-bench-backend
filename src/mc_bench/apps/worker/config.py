import os


class Settings:
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"


settings = Settings()
