"""A note kind is a type of note, e.g. observation, justification, hypothesis, etc.

A note kind has a name.
"""

from sqlalchemy import Column, Integer, String, Table

from .._metadata import metadata

note_kind = Table(
    "note_kind",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, unique=True, nullable=False),
    schema="research",
    comment=__doc__.strip(),
)
