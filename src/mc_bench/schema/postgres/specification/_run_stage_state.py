"""Defines the allowed states for run stages in the benchmark system.

This table defines the possible states a run stage can be in, such as pending, 
running, completed, or failed. It serves as a reference table for the state 
column in the run_stage table.
"""

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

# e.g. QUEUED, RUNNNIG, DONE
run_stage_state = Table(
    "run_stage_state",
    metadata,
    comment=__doc__.strip(),
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("slug", String, unique=True, nullable=False),
    schema="specification",
)
