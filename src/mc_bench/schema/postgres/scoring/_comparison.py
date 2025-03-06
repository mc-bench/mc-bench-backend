""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Column,
    ForeignKey,
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
    schema="scoring",
)
