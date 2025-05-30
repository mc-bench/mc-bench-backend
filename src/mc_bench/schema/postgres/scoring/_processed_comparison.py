"""
Tracks which comparisons have been processed for ELO calculations.
This prevents duplicate processing and helps maintain data integrity.
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

processed_comparison = Table(
    "processed_comparison",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column(
        "comparison_id", Integer, ForeignKey("scoring.comparison.id"), nullable=False
    ),
    # Ensure each comparison is only processed once
    UniqueConstraint("comparison_id", name="unique_processed_comparison"),
    schema="scoring",
)
