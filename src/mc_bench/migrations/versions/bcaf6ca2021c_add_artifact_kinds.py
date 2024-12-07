"""add artifact kinds

Revision ID: bcaf6ca2021c
Revises: f17051270c7b
Create Date: 2024-12-04 17:46:29.811067

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bcaf6ca2021c"
down_revision: Union[str, None] = "f17051270c7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KINDS = [
    "NORTHSIDE_CAPTURE_PNG",
    "EASTSIDE_CAPTURE_PNG",
    "SOUTHSIDE_CAPTURE_PNG",
    "WESTSIDE_CAPTURE_PNG",
    "BUILD_CINEMATIC_MP4",
]


def upgrade() -> None:
    for kind in KINDS:
        op.execute(
            sa.text(
                """INSERT INTO sample.artifact_kind (name) VALUES (:artifact_kind) ON CONFLICT DO NOTHING"""
            ).bindparams(artifact_kind=kind)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
