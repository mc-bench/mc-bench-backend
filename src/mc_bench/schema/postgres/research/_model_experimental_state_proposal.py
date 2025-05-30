from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Table,
    func,
    text,
)

from .._metadata import metadata

model_experimental_state_proposal = Table(
    "model_experimental_state_proposal",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("model_id", Integer, ForeignKey("specification.model.id"), nullable=False),
    Column(
        "new_experiment_state_id",
        Integer,
        ForeignKey("research.experimental_state.id"),
        nullable=False,
    ),
    Column("log_id", Integer, ForeignKey("research.log.id"), nullable=True),
    Column("accepted", Boolean, nullable=True),
    Column("accepted_at", TIMESTAMP(timezone=False), nullable=True),
    Column("accepted_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column("accepted_log_id", Integer, ForeignKey("research.log.id"), nullable=True),
    Column("rejected", Boolean, nullable=True),
    Column("rejected_at", TIMESTAMP(timezone=False), nullable=True),
    Column("rejected_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column("rejected_log_id", Integer, ForeignKey("research.log.id"), nullable=True),
    schema="research",
)
