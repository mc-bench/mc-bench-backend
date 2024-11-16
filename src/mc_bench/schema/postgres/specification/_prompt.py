"""
A prompt. This will include a template id (which should be the same across every given run).
This table is append only. If we choose to use a different template we should make a new prompt row.
"""

from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    ForeignKey,
    TIMESTAMP,
    func,
    BigInteger,
    UUID,
    text,
)
from .._metadata import metadata


prompt = Table(
    "prompt",
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
    Column("name", String, unique=True, nullable=False),
    Column("build_specification", String, nullable=False),
    comment=__doc__.strip(),
    schema="specification",
)
