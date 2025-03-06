""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Column,
    ForeignKey,
    Index,
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
    # While we can imagine most runs will occur as the result of a generation
    # it may become true that we execute individual runs that are not a part of the
    # generation concept
    Column(
        "generation_id",
        Integer,
        ForeignKey("specification.generation.id"),
        nullable=True,
    ),
    # Add index for model_id and prompt_id to speed up queries
    Index("ix_run_model_id_prompt_id", "model_id", "prompt_id"),
    schema="specification",
)
