"""add_comparison_report_table

Revision ID: 7c9848c3e794
Revises: 473407e9d86e
Create Date: 2025-03-15 17:16:33.833033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c9848c3e794'
down_revision: Union[str, None] = '473407e9d86e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
