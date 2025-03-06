""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    func,
    text,
)

from .._metadata import metadata

sample = Table(
    "sample",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column(
        "comparison_sample_id",
        UUID,
        nullable=False,
        server_default=text("uuid_generate_v4()"),
    ),
    Column(
        "run_id",
        Integer,
        ForeignKey("specification.run.id"),
        nullable=False,
    ),
    Column("result_inspiration_text", String, nullable=True),
    Column("result_description_text", String, nullable=True),
    Column("result_code_text", String, nullable=True),
    Column("raw", String, nullable=True),
    # indicates whether the sample is able to be voted on.
    Column(
        "active", Boolean, nullable=False, default=False, server_default=text("false")
    ),
    Column("comparison_correlation_id", UUID, nullable=True),
    Index(
        "sample_selection_index", "active", "comparison_correlation_id", "external_id"
    ),
    # indicates whether the sample is still undergoing processing
    Column(
        "is_pending", Boolean, nullable=False, default=True, server_default=text("true")
    ),
    # indicates whether the sample has everything it needs to be voted on
    Column(
        "is_complete",
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    ),
    # null - not yet approved or rejected, ids from scoring.sample_approval_state for approved or rejected
    Column(
        "approval_state_id",
        Integer,
        ForeignKey("scoring.sample_approval_state.id"),
        nullable=True,
    ),
    Column(
        "experimental_state_id",
        Integer,
        ForeignKey("research.experimental_state.id"),
        nullable=True,
    ),
    Column(
        "test_set_id",
        Integer,
        ForeignKey("sample.test_set.id"),
        nullable=True,
    ),
    schema="sample",
)
