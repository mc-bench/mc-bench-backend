""" """

from sqlalchemy import TIMESTAMP, Column, Integer, String, Table, func

from .._metadata import metadata

artifact_kind = Table(
    "artifact_kind",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("name", String, unique=True, nullable=False),
    schema="sample",
)
