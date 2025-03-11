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
