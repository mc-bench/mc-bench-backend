"""
Defines the provider table schema which stores different provider implementations for models.

This table represents various provider implementations (such as OpenAI, Anthropic, etc.) 
for machine learning models. Each provider has a specific provider_class that determines
how it is implemented, along with configuration settings used to connect to the relevant
API or service. Multiple providers can exist for the same model, allowing for different
implementations or API connections.
"""

from sqlalchemy import (
    JSON,
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

provider = Table(
    "provider",
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
    Column(
        "model_id",
        BigInteger,
        ForeignKey("specification.model.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "name",
        String,
        nullable=False,
    ),
    Column(
        "provider_class",
        String,
        ForeignKey("specification.provider_class.name"),
        nullable=False,
    ),
    Column("config", JSON, nullable=False),
    Column("is_default", Boolean, nullable=True),
    schema="specification",
)
