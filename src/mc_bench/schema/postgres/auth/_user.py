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

user = Table(
    "user",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("username", String(64), nullable=True, unique=True, index=True),
    Column("username_normalized", String(64), nullable=True, unique=True, index=True),
    Column("display_username", String(64), nullable=True, unique=True, index=True),
    Column(
        "canonical_identification_token_id",
        Integer,
        ForeignKey("auth.user_identification_token.id"),
        nullable=True,
    ),
    schema="auth",
)
