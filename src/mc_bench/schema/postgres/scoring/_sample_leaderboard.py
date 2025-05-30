"""
Tracks performance metrics for individual samples including ELO scores and win/loss statistics.
Used to identify strong and weak performers at the sample level.
"""

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    Table,
    UniqueConstraint,
    func,
)

from .._metadata import metadata

sample_leaderboard = Table(
    "sample_leaderboard",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column(
        "last_updated",
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ),
    Column("sample_id", Integer, ForeignKey("sample.sample.id"), nullable=False),
    Column("metric_id", Integer, ForeignKey("scoring.metric.id"), nullable=False),
    Column("test_set_id", Integer, ForeignKey("sample.test_set.id"), nullable=False),
    Column("elo_score", Float, nullable=False, default=1000.0),
    Column("vote_count", Integer, nullable=False, default=0),
    Column("win_count", Integer, nullable=False, default=0),
    Column("loss_count", Integer, nullable=False, default=0),
    Column("tie_count", Integer, nullable=False, default=0),
    # Ensure uniqueness for sample+metric+test_set combination
    UniqueConstraint(
        "sample_id", "metric_id", "test_set_id", name="unique_sample_leaderboard_entry"
    ),
    # Add indexes for leaderboard queries
    Index("ix_sample_leaderboard_elo_score", "elo_score"),
    Index("ix_sample_leaderboard_metric_test_set", "metric_id", "test_set_id"),
    schema="scoring",
)
