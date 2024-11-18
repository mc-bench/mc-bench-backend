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

permission = Table(
    "permission",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("name", String(64), unique=True, nullable=False),
    schema="auth",
)
