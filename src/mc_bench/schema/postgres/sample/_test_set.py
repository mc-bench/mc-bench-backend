"""A test set is a collection of samples that can be voted on."""

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

test_set = Table(
    "test_set",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("name", String, unique=True, nullable=False),
    Column("description", String, nullable=False),
    comment=__doc__.strip(),
    schema="sample",
)
