"""add artifact kinds

Revision ID: 503daea838dc
Revises: a4cbcbdc4a91
Create Date: 2024-12-04 14:14:55.460701

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "503daea838dc"
down_revision: Union[str, None] = "a4cbcbdc4a91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


KINDS = [
    "NBT_STRUCTURE_FILE",
    "PROMPT",
    "ORIGINAL_BUILD_SCRIPT_JS",
    "ORIGINAL_BUILD_SCRIPT_PY",
    "RAW_RESPONSE",
    "BUILD_SCHEMATIC",
    "BUILD_COMMAND_LIST",
    "BUILD_SUMMARY",
    "COMMAND_LIST_BUILD_SCRIPT_JS",
    "COMMAND_LIST_BUILD_SCRIPT_PY",
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
