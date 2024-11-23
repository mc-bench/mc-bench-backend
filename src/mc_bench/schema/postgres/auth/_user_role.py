from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    Table,
    UniqueConstraint,
    func,
)

from .._metadata import metadata

user_role = Table(
    "user_role",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("user_id", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("role_id", Integer, ForeignKey("auth.role.id"), nullable=False),
    UniqueConstraint("user_id", "role_id"),
    schema="auth",
)
