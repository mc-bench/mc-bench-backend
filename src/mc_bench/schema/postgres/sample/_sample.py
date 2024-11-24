""" """

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    BigInteger,
    Column,
    ForeignKey,
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
        "run_id",
        Integer,
        ForeignKey("specification.run.id"),
        nullable=False,
    ),
    Column("result_inspiration_text", String, nullable=True),
    Column("result_description_text", String, nullable=True),
    Column("result_code_text", String, nullable=True),
    Column("raw", String, nullable=True),
    comment=__doc__.strip(),
    schema="sample",
)
