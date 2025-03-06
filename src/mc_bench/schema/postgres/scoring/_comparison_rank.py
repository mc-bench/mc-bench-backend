"""
Table for storing sample rankings within comparisons.
This allows for ties and multi-sample comparisons beyond simple pairwise comparisons.
"""

from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Integer,
    Table,
    UniqueConstraint,
    func,
)

from .._metadata import metadata

comparison_rank = Table(
    "comparison_rank",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "comparison_id", Integer, ForeignKey("scoring.comparison.id"), nullable=False
    ),
    Column("sample_id", Integer, ForeignKey("sample.sample.id"), nullable=False),
    # Rank 1 = best, higher numbers = worse rank
    Column("rank", Integer, nullable=False),
    # Add created timestamp for audit trail
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    # Ensure a sample can only have one rank per comparison
    UniqueConstraint(
        "comparison_id", "sample_id", name="unique_sample_rank_per_comparison"
    ),
    schema="scoring",
)
