import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    INTERNAL_OBJECT_BUCKET = os.environ["INTERNAL_OBJECT_BUCKET"]


settings = Settings()
