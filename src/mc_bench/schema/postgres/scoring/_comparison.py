""" """

from sqlalchemy import (
    Table,
    Column,
    Integer,
    ForeignKey,
    UUID,
    text,
    func,
    TIMESTAMP,
)
from .._metadata import metadata


comparison = Table(
    "comparison",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("user_id", ForeignKey("auth.user.id"), nullable=False),
    Column(
        "comparison_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("metric_id", Integer, ForeignKey("scoring.metric.id"), nullable=False),
    Column("sample_1_id", Integer, ForeignKey("sample.sample.id"), nullable=False),
    Column("sample_2_id", Integer, ForeignKey("sample.sample.id"), nullable=False),
    Column(
        "winning_sample_id", Integer, ForeignKey("sample.sample.id"), nullable=False
    ),
    schema="scoring",
)
