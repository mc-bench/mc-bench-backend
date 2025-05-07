from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Table,
    func,
    text,
)

from .._metadata import metadata

__doc__ = """
Tracks proposals to change the experimental state of a template.

This table records when template experimental state change proposals are created,
by whom, and their acceptance or rejection status. It maintains references to 
the template being modified, the proposed new experimental state, and logs
associated with creation, acceptance, and rejection events.
"""

template_experimental_state_proposal = Table(
    "template_experimental_state_proposal",
    metadata,
    comment=__doc__.strip(),
    Column("id", Integer, primary_key=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column(
        "template_id", Integer, ForeignKey("specification.template.id"), nullable=False
    ),
    Column(
        "new_experiment_state_id",
        Integer,
        ForeignKey("research.experimental_state.id"),
        nullable=False,
    ),
    Column("log_id", Integer, ForeignKey("research.log.id"), nullable=True),
    Column("accepted", Boolean, nullable=True),
    Column("accepted_at", TIMESTAMP(timezone=False), nullable=True),
    Column("accepted_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column("accepted_log_id", Integer, ForeignKey("research.log.id"), nullable=True),
    Column("rejected", Boolean, nullable=True),
    Column("rejected_at", TIMESTAMP(timezone=False), nullable=True),
    Column("rejected_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column("rejected_log_id", Integer, ForeignKey("research.log.id"), nullable=True),
    schema="research",
)
