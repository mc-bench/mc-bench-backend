"""Add sorting strategy config

Revision ID: 3cb7f6ca1320
Revises: 1eeb63dd99cc
Create Date: 2025-03-11 16:01:21.966090

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3cb7f6ca1320"
down_revision: Union[str, None] = "1eeb63dd99cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO specification.scheduler_control (key, value, description)
        VALUES ('RUN_SORTING_STRATEGY', '"CREATED_ASC"', 'Defines how runs are sorted when enqueuing: CREATED_ASC, CREATED_DESC, or RANDOM')
        """
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
