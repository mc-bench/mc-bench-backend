"""add artifact kinds

Revision ID: f17051270c7b
Revises: 503daea838dc
Create Date: 2024-12-04 15:50:58.458347

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f17051270c7b"
down_revision: Union[str, None] = "503daea838dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KINDS = [
    "CONTENT_EXPORT_BUILD_SCRIPT_JS",
    "CONTENT_EXPORT_BUILD_SCRIPT_PY",
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
