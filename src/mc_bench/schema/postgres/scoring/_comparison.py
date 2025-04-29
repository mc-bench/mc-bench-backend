""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Column,
    ForeignKey,
    Index,
    Integer,
    Table,
    func,
    text,
)

from .._metadata import metadata

comparison = Table(
    "comparison",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("user_id", ForeignKey("auth.user.id"), nullable=True),
    Column(
        "comparison_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("metric_id", Integer, ForeignKey("scoring.metric.id"), nullable=False),
    Column("test_set_id", Integer, ForeignKey("sample.test_set.id"), nullable=False),
    Column("session_id", UUID, nullable=True),
    Column(
        "identification_token_id",
        Integer,
        ForeignKey("auth.user_identification_token.id"),
        nullable=True,
    ),
    # Add indexes for comparison table
    Index("ix_comparison_comparison_id", "comparison_id"),
    Index("ix_comparison_metric_test_set", "metric_id", "test_set_id"),
    schema="scoring",
)

comparison_rank = Table(
    "comparison_rank",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("comparison_id", Integer, ForeignKey("scoring.comparison.id"), nullable=False),
    Column("sample_id", Integer, ForeignKey("sample.sample.id"), nullable=False),
    Column("rank", Integer, nullable=False),
    Index("ix_comparison_rank_comparison_id", "comparison_id"),
    Index("ix_comparison_rank_sample_id", "sample_id"),
    schema="scoring",
)

processed_comparison = Table(
    "processed_comparison",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("comparison_id", Integer, ForeignKey("scoring.comparison.id"), nullable=False),
    Index("ix_processed_comparison_comparison_id", "comparison_id"),
    schema="scoring",
)
