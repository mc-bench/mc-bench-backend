"""
Tracks model performance metrics including ELO scores and win/loss statistics.
Used to generate leaderboards across different metrics and test sets.
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

model_leaderboard = Table(
    "model_leaderboard",
    metadata,
    comment=__doc__.strip(),
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
    Column("model_id", Integer, ForeignKey("specification.model.id"), nullable=False),
    Column("metric_id", Integer, ForeignKey("scoring.metric.id"), nullable=False),
    Column("test_set_id", Integer, ForeignKey("sample.test_set.id"), nullable=False),
    Column("tag_id", Integer, ForeignKey("specification.tag.id"), nullable=True),
    Column("elo_score", Float, nullable=False, default=1000.0),
    Column("vote_count", Integer, nullable=False, default=0),
    Column("win_count", Integer, nullable=False, default=0),
    Column("loss_count", Integer, nullable=False, default=0),
    Column("tie_count", Integer, nullable=False, default=0),
    # Ensure uniqueness for model+metric+test_set+collection combination
    UniqueConstraint(
        "model_id",
        "metric_id",
        "test_set_id",
        "tag_id",
        name="unique_model_leaderboard_entry",
    ),
    # Add indexes for leaderboard queries
    Index("ix_model_leaderboard_elo_score", "elo_score"),
    Index(
        "ix_model_leaderboard_metric_test_set_tag_vote",
        "metric_id",
        "test_set_id",
        "tag_id",
        "vote_count",
    ),
    schema="scoring",
)
