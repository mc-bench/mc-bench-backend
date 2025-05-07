"""Association table that implements a many-to-many relationship between prompts and tags.
This allows prompts to be categorized and organized with multiple tags, enabling
better searchability and organization of prompts in the system.
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

prompt_tag = Table(
    "prompt_tag",
    metadata,
    comment=__doc__.strip(),
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
