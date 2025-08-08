"""
Table for storing scheduler control values that allow dynamic configuration of the scheduler system
without requiring code changes. These values can be used to enable/disable features, set limits,
or control scheduler behavior at runtime.
"""

from sqlalchemy import TIMESTAMP, Column, Index, String, Table, func
from sqlalchemy.dialects.postgresql import UUID

from mc_bench.schema.postgres._metadata import metadata

scheduler_control = Table(
    comment=__doc__.strip(),
    "scheduler_control",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
        comment="Primary key for the scheduler control value",
    ),
    Column(
        "key",
        String,
        nullable=False,
        unique=True,
        comment="The control key (e.g., MAX_QUEUED_TASKS, SCHEDULER_MODE)",
    ),
    Column(
        "value",
        String,
        nullable=False,
        comment="JSON serialized value for the control setting",
    ),
    Column(
        "description",
        String,
        nullable=True,
        comment="Description of what this control value does",
    ),
    Column(
        "created",
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        nullable=False,
    ),
    Column(
        "last_modified",
        TIMESTAMP(timezone=False),
        nullable=True,
    ),
    schema="specification",
)

# Create an index on the key field for faster lookups
Index("idx_scheduler_control_key", scheduler_control.c.key)
