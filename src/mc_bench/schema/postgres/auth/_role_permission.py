from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func, UniqueConstraint,
)

from .._metadata import metadata

role_permission = Table(
    "role_permission",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("role_id", Integer, ForeignKey("auth.role.id"), nullable=False),
    Column("permission_id", Integer, ForeignKey("auth.permission.id"), nullable=False),
    UniqueConstraint("role_id", "permission_id"),
    schema="auth",
)
