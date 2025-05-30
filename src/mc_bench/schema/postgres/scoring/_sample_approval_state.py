"""Valid sample approval states"""

from sqlalchemy import TIMESTAMP, Column, Integer, String, Table, func

from .._metadata import metadata

sample_approval_state = Table(
    "sample_approval_state",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("name", String, unique=True, nullable=False),
    schema="scoring",
)
