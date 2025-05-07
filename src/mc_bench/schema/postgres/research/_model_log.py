"""A bridge table between a model and a log"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from .._metadata import metadata

model_log = Table(
    "model_log",
    metadata,
    Column("model_id", Integer, ForeignKey("specification.model.id"), nullable=False),
    Column("log_id", Integer, ForeignKey("research.log.id"), nullable=False),
    comment=__doc__.strip(),
    schema="research",
)
