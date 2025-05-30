"""A log is an entry indicating an observation or an action

A log has an action and a note.
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

log = Table(
    "log",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column(
        "action_slug", String, ForeignKey("research.log_action.name"), nullable=False
    ),
    Column("note_id", Integer, ForeignKey("research.note.id"), nullable=False),
    schema="research",
    comment=__doc__.strip(),
)
