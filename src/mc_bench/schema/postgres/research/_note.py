"""A note is a narrative entry by a person or SYSTEM

A note has a kind, content, and a created timestamp.
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

note = Table(
    "note",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("deleted", TIMESTAMP(timezone=False), nullable=True),
    Column("deleted_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("kind_slug", String, ForeignKey("research.note_kind.name"), nullable=False),
    Column("content", String, nullable=False),
    schema="research",
    comment=__doc__.strip(),
)
