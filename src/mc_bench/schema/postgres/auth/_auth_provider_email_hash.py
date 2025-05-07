"""
Maps hashed email addresses to users from external authentication providers.

This table stores relationships between external authentication providers, their users,
and the corresponding local user accounts. Email hashes are used to protect user privacy
while still allowing for user identification across different authentication providers.
The table enforces uniqueness of email hash per auth provider to prevent duplicate accounts.
"""

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)

from .._metadata import metadata

auth_provider_email_hash = Table(
    "auth_provider_email_hash",
    metadata,
    comment=__doc__.strip(),
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column(
        "auth_provider_id", Integer, ForeignKey("auth.auth_provider.id"), nullable=False
    ),
    Column("auth_provider_user_id", String, nullable=False),
    Column("user_id", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("email_hash", String, nullable=False),
    # We never want to permit a duplicate email hash from the same auth provider
    UniqueConstraint("auth_provider_id", "email_hash"),
    schema="auth",
)
