""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Column,
    ForeignKey,
    Integer,
    Table,
    UniqueConstraint,
    func,
    text,
)

from .._metadata import metadata

user_identification_token = Table(
    "user_identification_token",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("token", UUID, nullable=False, server_default=text("uuid_generate_v4()")),
    Column("user_id", ForeignKey("auth.user.id"), nullable=True),
    Column(
        "created_at",
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        nullable=False,
    ),
    Column(
        "last_used_at",
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        nullable=False,
    ),
    UniqueConstraint("token", "user_id", name="uq_token_user_id"),
    schema="auth",
)
