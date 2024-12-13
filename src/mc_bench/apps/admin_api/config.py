import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JWT_SECRET_KEY = os.environ["SECRET_KEY"]
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


settings = Settings()
