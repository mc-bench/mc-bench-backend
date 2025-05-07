"""A bridge table between a template and a log"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from .._metadata import metadata

template_log = Table(
    "template_log",
    metadata,
    Column(
        "template_id", Integer, ForeignKey("specification.template.id"), nullable=False
    ),
    Column("log_id", Integer, ForeignKey("research.log.id"), nullable=False),
    comment=__doc__.strip(),
    schema="research",
)
