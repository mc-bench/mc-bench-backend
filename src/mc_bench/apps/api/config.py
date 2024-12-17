import os


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
    X_CLIENT_ID = os.getenv("X_CLIENT_ID")
    X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
    X_EMAIL_SALT = os.getenv("X_EMAIL_SALT")
    REDIRECT_URI = "http://127.0.0.1:5173/login" # os.getenv("REDIRECT_URI", "http://localhost:5173/login")


settings = Settings()
