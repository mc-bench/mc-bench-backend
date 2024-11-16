""" """

from sqlalchemy import Table, Column, Integer, String, func, TIMESTAMP

from .._metadata import metadata

artifact_kind = Table(
    "artifact_kind",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("name", String, unique=True, nullable=False),
    comment=__doc__.strip(),
    schema="sample",
)
