"""Run stage table with indexes for optimized scheduler performance"""

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Column,
    ForeignKey,
    Index,
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
        "last_modified",
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        nullable=True,
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
    # Celery task ID for tracking and revocation
    Column("task_id", String(255), nullable=True),
    # Timestamp for heartbeat monitoring
    Column("heartbeat", TIMESTAMP(timezone=False), nullable=True),
    # Indexes for efficient scheduler queries
    Index("ix_run_stage_state_id", "state_id"),
    Index("ix_run_stage_heartbeat", "heartbeat"),
    Index("ix_run_stage_run_id", "run_id"),
    Index("ix_run_stage_stage_slug", "stage_slug"),
    # Composite index for the most common scheduler query patterns
    Index("ix_run_stage_state_id_heartbeat", "state_id", "heartbeat"),
    schema="specification",
)
