from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
)

from .._metadata import metadata

role = Table(
    "role",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column("name", String, unique=True, nullable=False),
    schema="auth",
)
