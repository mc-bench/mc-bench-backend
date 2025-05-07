"""Stores categorization tags that can be applied to prompts and potentially other entities.

Tags enable organization, filtering, and grouping of related items. Each tag has a unique name
and can be configured to participate in scoring calculations through the calculate_score flag.
"""

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

tag = Table(
    "tag",
    metadata,
    comment=__doc__.strip(),
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("name", String(64), unique=True, nullable=False),
    Column("calculate_score", Boolean, nullable=False, server_default=text("true")),
    schema="specification",
)
