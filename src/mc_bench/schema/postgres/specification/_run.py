""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    Table,
    func,
    text,
)

from .._metadata import metadata

run = Table(
    "run",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("template_id", Integer, ForeignKey("specification.template.id")),
    Column("prompt_id", Integer, ForeignKey("specification.prompt.id")),
    Column("model_id", Integer, ForeignKey("specification.model.id")),
    Column("state_id", Integer, ForeignKey("specification.run_state.id")),
    comment=__doc__.strip(),
    schema="specification",
)
