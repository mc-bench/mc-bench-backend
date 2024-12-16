"""Add code validation stage

Revision ID: 1eef5895e9f2
Revises: 688482827ae4
Create Date: 2024-12-16 16:26:35.638632

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1eef5895e9f2"
down_revision: Union[str, None] = "688482827ae4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAGES = [
    "CODE_VALIDATION",
]


def upgrade() -> None:
    for stage in STAGES:
        op.execute(
            sa.text(
                """\
                INSERT INTO specification.stage (created_by, slug) values (
                    (SELECT id from auth.user where username = 'SYSTEM'),
                    :slug
                )
                ON CONFLICT (slug) DO NOTHING
            """
            ).bindparams(slug=stage)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
