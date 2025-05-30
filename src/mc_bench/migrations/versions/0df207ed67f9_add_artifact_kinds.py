"""add artifact kinds

Revision ID: 0df207ed67f9
Revises: 1b9505818e11
Create Date: 2024-12-01 00:40:04.923558

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0df207ed67f9"
down_revision: Union[str, None] = "1b9505818e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KINDS = ["BUILD_SCHEMATIC", "BUILD_GLTF"]


def upgrade() -> None:
    for kind in KINDS:
        op.execute(
            sa.text("""\
        INSERT INTO sample.artifact_kind (name) VALUES (:artifact_kind)
        
        """).bindparams(artifact_kind=kind)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
