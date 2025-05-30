"""A log action is a reason for making a log entry

A log action has a name.
"""

from sqlalchemy import Column, Integer, String, Table

from .._metadata import metadata

log_action = Table(
    "log_action",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, unique=True, nullable=False),
    comment=__doc__.strip(),
    schema="research",
)
