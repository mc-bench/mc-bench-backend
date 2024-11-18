import os


class Settings:
    GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
    GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]
    JWT_SECRET_KEY = os.environ["SECRET_KEY"]
    GITHUB_EMAIL_SALT = os.environ["GITHUB_EMAIL_SALT"]
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


settings = Settings()
