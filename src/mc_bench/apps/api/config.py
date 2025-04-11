import logging
import os


class Settings:
    GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
    GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]
    JWT_SECRET_KEY = os.environ["SECRET_KEY"]
    GITHUB_EMAIL_SALT = os.environ["GITHUB_EMAIL_SALT"]
    EMAIL_SALT = os.environ["GITHUB_EMAIL_SALT"]
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    REFRESH_TOKEN_EXPIRE_MINUTES = int(
        os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES", 60 * 24 * 30)
    )
    AUTO_GRANT_ADMIN_ROLE = os.environ.get("AUTO_GRANT_ADMIN_ROLE", "false") == "true"

    EXTERNAL_OBJECT_BUCKET = os.environ.get("EXTERNAL_OBJECT_BUCKET")
    INTERNAL_OBJECT_BUCKET = os.environ.get("INTERNAL_OBJECT_BUCKET")

    # New settings for Google OAuth
    GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
    GOOGLE_REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"
    LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO")
    LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)

    # Feature flags
    USE_PRIORITY_COMPARISON = os.environ.get("USE_PRIORITY_COMPARISON", "false") == "true"


settings = Settings()
