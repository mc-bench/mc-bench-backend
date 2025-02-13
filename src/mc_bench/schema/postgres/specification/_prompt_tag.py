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

prompt_tag = Table(
    "prompt_tag",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("prompt_id", Integer, ForeignKey("specification.prompt.id"), nullable=False),
    Column("tag_id", Integer, ForeignKey("specification.tag.id"), nullable=False),
    UniqueConstraint("prompt_id", "tag_id"),
    schema="specification",
)
