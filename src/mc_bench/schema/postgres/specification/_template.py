""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

template = Table(
    "template",
    metadata,
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
    Column("name", String, unique=True, nullable=False),
    Column("description", String, unique=False, nullable=True),
    Column("content", String, nullable=False),
    Column("active", Boolean, nullable=True),
    Column("frozen", Boolean, nullable=True),
    Column("minecraft_version", String, nullable=False),
    Column(
        "experimental_state_id",
        Integer,
        ForeignKey("research.experimental_state.id"),
        nullable=True,
    ),
    schema="specification",
)
