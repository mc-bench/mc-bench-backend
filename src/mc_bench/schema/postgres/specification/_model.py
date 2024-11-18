"""
A reference table of model names, such as "NousResearch/Hermes-3-Llama-3.1-8B" (from hugging face) or "claude-3-5-sonnet-20240620".

While some systems may have specific variants, we will mediate any of these differences by recording timestamps and other
metadata for how the model was run, accessed, or called.

Unless it becomes necessary, we will generally consider this model name the system under test.
"""

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

model = Table(
    "model",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("name", String, unique=True, nullable=False),
    comment=__doc__.strip(),
    schema="specification",
)
