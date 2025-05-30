import logging
import os


class Settings:
    INTERNAL_OBJECT_BUCKET = os.environ["INTERNAL_OBJECT_BUCKET"]
    EXTERNAL_OBJECT_BUCKET = os.environ["EXTERNAL_OBJECT_BUCKET"]
    FAST_RENDER = os.environ.get("FAST_RENDER") == "true"
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS") == "true"
    BLENDER_RENDER_CORES = int(os.environ.get("BLENDER_RENDER_CORES", 1))
    LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO")
    LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)
    # Configure how frequently to log block placement at INFO level
    LOG_INTERVAL_BLOCKS = int(os.environ.get("LOG_INTERVAL_BLOCKS", "100"))
    # Configure how frequently to log materials baked at INFO level
    LOG_INTERVAL_MATERIALS = int(os.environ.get("LOG_INTERVAL_MATERIALS", "10"))


settings = Settings()
