"""
Junction table linking roles to permissions in a many-to-many relationship.

This table maps which permissions are assigned to each role, allowing for flexible
role-based access control. Each row represents a single permission granted to a specific role.
The table enforces uniqueness constraints to prevent duplicate role-permission assignments.
"""

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

role_permission = Table(
    "role_permission",
    metadata,
    comment=__doc__.strip(),
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
