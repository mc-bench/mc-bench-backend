"""A bridge table between a sample and a log"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from .._metadata import metadata

sample_log = Table(
    "sample_log",
    metadata,
    Column("sample_id", Integer, ForeignKey("sample.sample.id"), nullable=False),
    Column("log_id", Integer, ForeignKey("research.log.id"), nullable=False),
    schema="research",
)
