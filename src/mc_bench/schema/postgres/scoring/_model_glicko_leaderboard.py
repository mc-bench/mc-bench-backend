"""
Tracks model performance metrics using Glicko-2 rating system.
Used to generate Glicko-2 leaderboards across different metrics and test sets.
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

model_glicko_leaderboard = Table(
    "model_glicko_leaderboard",
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
    Column("model_id", Integer, ForeignKey("specification.model.id"), nullable=False),
    Column("metric_id", Integer, ForeignKey("scoring.metric.id"), nullable=False),
    Column("test_set_id", Integer, ForeignKey("sample.test_set.id"), nullable=False),
    Column("tag_id", Integer, ForeignKey("specification.tag.id"), nullable=True),
    Column("glicko_rating", Float, nullable=False, default=1000.0),
    Column("rating_deviation", Float, nullable=False, default=350.0),
    Column("volatility", Float, nullable=False, default=0.06),
    Column("vote_count", Integer, nullable=False, default=0),
    Column("win_count", Integer, nullable=False, default=0),
    Column("loss_count", Integer, nullable=False, default=0),
    Column("tie_count", Integer, nullable=False, default=0),
    # Ensure uniqueness for model+metric+test_set+tag combination
    UniqueConstraint(
        "model_id",
        "metric_id",
        "test_set_id",
        "tag_id",
        name="unique_model_glicko_leaderboard_entry",
    ),
    # Add indexes for leaderboard queries
    Index("ix_model_glicko_leaderboard_rating", "glicko_rating"),
    Index(
        "ix_model_glicko_leaderboard_metric_test_set_tag_vote",
        "metric_id",
        "test_set_id",
        "tag_id",
        "vote_count",
    ),
    schema="scoring",
) 