"""
Junction table linking users to roles in a many-to-many relationship.

This table associates users with their assigned roles for authorization purposes.
Each record represents a single role assignment to a specific user. The table
enforces uniqueness constraints to prevent duplicate user-role assignments.
Role assignments determine what permissions and access levels a user has within
the application.
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

user_role = Table(
    "user_role",
    metadata,
    comment=__doc__.strip(),
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
