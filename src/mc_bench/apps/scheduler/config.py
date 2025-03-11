import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from mc_bench.models.scheduler_control import SchedulerControl
from mc_bench.util.postgres import managed_session


class Settings:
    # Auth settings for token generation
    JWT_SECRET_KEY = os.environ["SECRET_KEY"]
    ALGORITHM = "HS256"

    SCHEDULER_INTERVAL = int(os.environ.get("SCHEDULER_INTERVAL", "5"))

    DEFAULT_MAX_QUEUED_TASKS = int(os.environ.get("DEFAULT_MAX_QUEUED_TASKS", "0"))

    # Heartbeat monitoring settings
    HEARTBEAT_TIMEOUT_SECONDS = int(
        os.environ.get("SCHEDULER_HEARTBEAT_TIMEOUT", "180")
    )  # Default 3 minutes

    # Advanced settings for large-scale deployments
    MAX_STALLED_TASKS_PER_CHECK = int(
        os.environ.get("SCHEDULER_MAX_STALLED_TASKS", "10")
    )  # Process more stalled tasks

    MAX_FAILED_STAGES_PER_CHECK = int(
        os.environ.get("SCHEDULER_MAX_FAILED_STAGES", "10")
    )  # Process more failed stages

    # Logging settings
    HUMANIZE_LOGS = os.environ.get("HUMANIZE_LOGS", "false") == "true"
    LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO")
    LOG_LEVEL = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)

    # Control setting keys
    SCHEDULER_MODE_KEY = "SCHEDULER_MODE"
    DEFAULT_MAX_TASKS_KEY = "DEFAULT_MAX_QUEUED_TASKS"
    SCHEDULER_INTERVAL_KEY = "SCHEDULER_INTERVAL"
    HEARTBEAT_TIMEOUT_KEY = "HEARTBEAT_TIMEOUT_SECONDS"
    HEARTBEAT_INTERVAL_KEY = "HEARTBEAT_MONITOR_INTERVAL"
    MAX_STALLED_TASKS_KEY = "MAX_STALLED_TASKS_PER_CHECK"
    MAX_FAILED_STAGES_KEY = "MAX_FAILED_STAGES_PER_CHECK"

    # queue specific settings
    MAX_TASKS_PROMPT_KEY = "MAX_TASKS_prompt"
    MAX_TASKS_RENDER_KEY = "MAX_TASKS_render"
    MAX_TASKS_POST_PROCESS_KEY = "MAX_TASKS_post_process"
    MAX_TASKS_PARSE_KEY = "MAX_TASKS_parse"
    MAX_TASKS_SERVER_KEY = "MAX_TASKS_server"
    MAX_TASKS_VALIDATE_KEY = "MAX_TASKS_validate"
    MAX_TASKS_PREPARE_KEY = "MAX_TASKS_prepare"

    @staticmethod
    def get_control_value(db: Session, key: str, default: Optional[any] = None) -> any:
        """Get a control value from the database or return the default."""
        value = SchedulerControl.get_value(db, key)
        return value if value is not None else default

    @staticmethod
    def get_scheduler_mode(db: Session) -> str:
        """Get the scheduler mode setting."""
        mode = Settings.get_control_value(db, Settings.SCHEDULER_MODE_KEY, "on")
        return mode.lower()

    def refresh_control_values(self, db: Session) -> None:
        """
        Refresh control values from the database.

        This updates the instance attributes using values from the database,
        falling back to environment variables if not set in the database.
        """
        # Get all controls at once to minimize DB queries
        controls = SchedulerControl.get_all_controls(db)

        # Update settings with database values, falling back to environment defaults
        self.DEFAULT_MAX_QUEUED_TASKS = controls.get(
            self.DEFAULT_MAX_TASKS_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )
        self.SCHEDULER_INTERVAL = controls.get(
            self.SCHEDULER_INTERVAL_KEY, self.SCHEDULER_INTERVAL
        )
        self.HEARTBEAT_TIMEOUT_SECONDS = controls.get(
            self.HEARTBEAT_TIMEOUT_KEY, self.HEARTBEAT_TIMEOUT_SECONDS
        )
        self.MAX_STALLED_TASKS_PER_CHECK = controls.get(
            self.MAX_STALLED_TASKS_KEY, self.MAX_STALLED_TASKS_PER_CHECK
        )
        self.MAX_FAILED_STAGES_PER_CHECK = controls.get(
            self.MAX_FAILED_STAGES_KEY, self.MAX_FAILED_STAGES_PER_CHECK
        )
        self.MAX_TASKS_PROMPT = controls.get(
            self.MAX_TASKS_PROMPT_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )
        self.MAX_TASKS_RENDER = controls.get(
            self.MAX_TASKS_RENDER_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )
        self.MAX_TASKS_POST_PROCESS = controls.get(
            self.MAX_TASKS_POST_PROCESS_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )
        self.MAX_TASKS_PARSE = controls.get(
            self.MAX_TASKS_PARSE_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )
        self.MAX_TASKS_SERVER = controls.get(
            self.MAX_TASKS_SERVER_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )
        self.MAX_TASKS_VALIDATE = controls.get(
            self.MAX_TASKS_VALIDATE_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )
        self.MAX_TASKS_PREPARE = controls.get(
            self.MAX_TASKS_PREPARE_KEY, self.DEFAULT_MAX_QUEUED_TASKS
        )


settings = Settings()


def refresh_settings():
    """Refresh settings from the database."""
    with managed_session() as db:
        settings.refresh_control_values(db)
