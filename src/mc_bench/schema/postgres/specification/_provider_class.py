"""
Provider class definitions for LLM service integration.

This table defines the types of model providers available in the system (like OpenAI, 
Anthropic, Gemini, etc.) and stores their default configuration settings. Each provider 
class represents a different implementation strategy for connecting to LLM services.
"""

from sqlalchemy import (
    JSON,
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

provider_class = Table(
    "provider_class",
    metadata,
    comment=__doc__.strip(),
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
    Column("default_config", JSON, nullable=False, server_default=text("'{}'::jsonb")),
    schema="specification",
)
