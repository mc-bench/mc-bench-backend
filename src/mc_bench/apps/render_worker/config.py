import os


class Settings:
    INTERNAL_OBJECT_BUCKET = os.environ["INTERNAL_OBJECT_BUCKET"]
    EXTERNAL_OBJECT_BUCKET = os.environ["EXTERNAL_OBJECT_BUCKET"]
    FAST_RENDER = os.environ["FAST_RENDER"] == "true"


settings = Settings()
