"""This module defines the 'metric' table schema for storing scoring metrics.

The metric table contains definitions of different metrics used to evaluate model outputs,
including human-judged qualities like helpfulness, correctness, and other dimensions
used in model evaluations. Each metric has a name, description, and tracking metadata.
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

metric = Table(
    "metric",
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
    Column("name", String(), unique=True, nullable=False),
    Column("description", String(), nullable=False),
    schema="scoring",
)
