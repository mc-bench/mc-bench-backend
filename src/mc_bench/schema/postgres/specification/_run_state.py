""" """

from sqlalchemy import (
    Column,
    Table,
    Integer,
    String,
    TIMESTAMP,
    func,
    UUID,
    ForeignKey,
    text,
    BigInteger,
)
from .._metadata import metadata

# e.g. QUEUED, RUNNNIG, DONE
run_state = Table(
    "run_state",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=False
    ),
    Column("created_by", Integer, ForeignKey("auth.user.id"), nullable=False),
    Column("last_modified", TIMESTAMP(timezone=False), nullable=True),
    Column("last_modified_by", Integer, ForeignKey("auth.user.id"), nullable=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column("slug", String, unique=True, nullable=False),
    comment=__doc__.strip(),
    schema="specification",
)
