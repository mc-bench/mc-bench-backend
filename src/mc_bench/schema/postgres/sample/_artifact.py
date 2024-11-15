""" """

from sqlalchemy import Table, Column, Integer, String, ForeignKey, func, TIMESTAMP
from .._metadata import metadata


artifact = Table(
    "artifact",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column(
        "artifact_kind_id",
        Integer,
        ForeignKey("sample.artifact_kind.id"),
        nullable=False,
    ),
    Column(
        "run_model_id",
        Integer,
        ForeignKey("specification.run_model.id"),
        nullable=False,
    ),
    Column("bucket", String, unique=False, nullable=False),
    Column("key", String, unique=False, nullable=False),
    comment=__doc__.strip(),
    schema="sample",
)
