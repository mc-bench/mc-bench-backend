"""
This table represents a request to generate content using a specific model and prompt.
A generation may result in multiple individual runs as part of the content creation process.
Generations track the higher-level process of content creation, while individual runs track
specific model executions.
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

generation = Table(
    "generation",
    metadata,
    comment=__doc__.strip(),
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("name", String, nullable=False),
    Column("description", String, nullable=False),
    Column(
        "state_id",
        BigInteger,
        ForeignKey("specification.generation_state.id"),
        nullable=False,
    ),
    Column(
        "default_test_set_id",
        BigInteger,
        ForeignKey("sample.test_set.id"),
        nullable=True,
    ),
    schema="specification",
)
