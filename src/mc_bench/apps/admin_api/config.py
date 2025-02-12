import os


class Settings:
    JWT_SECRET_KEY = os.environ["SECRET_KEY"]
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"


settings = Settings()
