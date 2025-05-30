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
