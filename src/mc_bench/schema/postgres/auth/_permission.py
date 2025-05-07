"""
Permissions table storing granular access controls for the application.

This table defines individual permissions that can be granted to roles in the system.
Each permission represents a specific action or access level that can be assigned
to users through role associations. Permissions have unique names that identify
the specific capability they grant within the application.
"""

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
    comment=__doc__.strip(),
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("name", String(64), unique=True, nullable=False),
    schema="auth",
)
