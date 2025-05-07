"""
The artifact_kind table represents the different types of artifacts that can be tracked in the system.
It serves as a lookup/reference table to categorize artifacts based on their nature or purpose.
Each artifact kind has a unique name and is used to classify artifacts in a consistent manner.
"""

from sqlalchemy import TIMESTAMP, Column, Integer, String, Table, func

from .._metadata import metadata

artifact_kind = Table(
    "artifact_kind",
    metadata,
    comment=__doc__.strip(),
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("name", String, unique=True, nullable=False),
    schema="sample",
)
