"""
Defines the valid states for sample approval in the evaluation workflow.

This table stores the possible states that a sample can have during the approval process,
such as pending, approved, rejected, etc. These states are used to track the progress
of samples through the evaluation workflow.

Each state represents a distinct phase in the approval lifecycle, allowing for structured
workflow management and status tracking. The states typically follow a progression from
initial submission through review and final determination.
"""

from sqlalchemy import TIMESTAMP, Column, Integer, String, Table, func

from .._metadata import metadata

sample_approval_state = Table(
    "sample_approval_state",
    metadata,
    comment=__doc__.strip(),
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("name", String, unique=True, nullable=False),
    schema="scoring",
)
