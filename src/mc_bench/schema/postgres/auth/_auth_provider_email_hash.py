from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    ForeignKey,
    UniqueConstraint,
    BigInteger,
    func,
    TIMESTAMP,
)
from .._metadata import metadata


auth_provider_email_hash = Table(
    "auth_provider_email_hash",
    metadata,
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
