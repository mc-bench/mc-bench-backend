"""A bridge table between a prompt and a log"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from .._metadata import metadata

prompt_log = Table(
    "prompt_log",
    metadata,
    Column("prompt_id", Integer, ForeignKey("specification.prompt.id"), nullable=False),
    Column("log_id", Integer, ForeignKey("research.log.id"), nullable=False),
    comment=__doc__.strip(),
    schema="research",
)
