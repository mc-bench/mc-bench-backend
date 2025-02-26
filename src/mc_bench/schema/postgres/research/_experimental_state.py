"""Valid experimental states

- DRAFT - initial state, thing is not ready for use
- IN_REVIEW - thing is ready for use, but not yet approved
- RELEASED - thing is ready for use
- DEPRECATED - thing is no longer for use
- EXPERIMENTAL - thing is experimental and not ready for use
- REJECTED - thing is rejected and not ready for use

"""

from sqlalchemy import TIMESTAMP, UUID, Column, Integer, String, Table, func, text

from .._metadata import metadata

experimental_state = Table(
    "experimental_state",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "external_id", UUID, nullable=False, server_default=text("uuid_generate_v4()")
    ),
    Column(
        "created", TIMESTAMP(timezone=False), server_default=func.now(), nullable=True
    ),
    Column("name", String, unique=True, nullable=False),
    schema="research",
)
