"""Table defining the possible states a generation can be in during its lifecycle.

This table stores the various states that a generation can transition through,
such as queued, processing, completed, or failed. Each state is uniquely
identified and tracked with creation and modification metadata.
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

generation_state = Table(
    "generation_state",
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
