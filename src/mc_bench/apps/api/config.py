import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
    GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]
    JWT_SECRET_KEY = os.environ["SECRET_KEY"]
    GITHUB_EMAIL_SALT = os.environ["GITHUB_EMAIL_SALT"]
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    REFRESH_TOKEN_EXPIRE_MINUTES = int(
        os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES", 60 * 24 * 30)
    )


settings = Settings()
