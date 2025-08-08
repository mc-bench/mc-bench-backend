"""
Stores authentication tokens that can be used to identify users.

This table manages token-based authentication for users in the system. Each record
contains a unique UUID token associated with a user account that can be used for
session management, API authentication, or other identification purposes.
The table tracks when tokens are created and last used to support token expiration
and activity monitoring.
"""

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
    comment=__doc__.strip(),
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
