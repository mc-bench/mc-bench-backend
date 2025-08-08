"""
Authentication provider table that stores information about external identity providers.

This table stores references to third-party authentication systems such as GitHub, Google, 
or other OAuth providers that can be used for user authentication in the application.
Each entry represents a different provider with a unique name.
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

auth_provider = Table(
    "auth_provider",
    metadata,
    comment=__doc__.strip(),
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column("name", String, nullable=False, unique=True),
    schema="auth",
)
