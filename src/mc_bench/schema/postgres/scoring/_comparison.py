"""
Comparison table for storing user or system evaluations of model outputs.

This table tracks comparison data for model samples across different metrics and test sets.
It stores information about who performed the comparison (user_id or identification_token_id),
when it was created, which metric and test set were used, and additional tracking data like
session_id and comparison_id for grouping related comparisons.
"""

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
    comment=__doc__.strip(),
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
