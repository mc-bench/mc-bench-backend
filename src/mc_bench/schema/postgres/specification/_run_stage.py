""" """

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

run_stage = Table(
    "run_stage",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("run_id", Integer, ForeignKey("specification.run.id"), nullable=False),
    Column("stage_id", Integer, ForeignKey("specification.stage.id"), nullable=False),
    Column(
        "stage_slug",
        String(255),
        ForeignKey("specification.stage.slug"),
        nullable=False,
    ),
    Column(
        "state_id",
        Integer,
        ForeignKey("specification.run_stage_state.id"),
        nullable=False,
    ),
    schema="specification",
)
