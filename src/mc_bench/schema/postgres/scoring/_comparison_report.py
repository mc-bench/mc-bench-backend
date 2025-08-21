"""Table for storing user reports on comparisons."""

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func, text

from .._metadata import metadata

comparison_report = Table(
    "comparison_report",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("external_id", Text, server_default=text("uuid_generate_v4()"), unique=True),
    Column("comparison_id", ForeignKey("scoring.comparison.id"), nullable=False),
    Column("user_id", ForeignKey("auth.user.id"), nullable=True),  # Optional for authenticated users
    Column(
        "identification_token_id",
        Integer,
        ForeignKey("auth.user_identification_token.id"),
        nullable=False, 
    ),
    Column(
        "report_reason",
        Enum(
            "inappropriate",
            "spam",
            "irrelevant",
            "duplicate",
            "other",
            name="report_reason_enum",
        ),
        nullable=False,
    ),
    Column("report_details", Text, nullable=True),  # Optional additional details
    Column("created", TIMESTAMP, server_default=func.now()),
    Column("last_modified", TIMESTAMP, server_default=func.now(), onupdate=func.now()),
    Index("ix_comparison_report_comparison_id", "comparison_id"),
    Index("ix_comparison_report_identification_token_id", "identification_token_id"),
    UniqueConstraint(
        "comparison_id", 
        "identification_token_id",
        name="uq_comparison_report_unique_reporter",
    ),
    schema="scoring",
)