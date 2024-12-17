"""Add x auth provider

Revision ID: d8c226689cf2
Revises: 1eef5895e9f2
Create Date: 2024-12-17 16:41:42.183910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8c226689cf2'
down_revision: Union[str, None] = '1eef5895e9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""\
            INSERT INTO auth.auth_provider (name, created_by)
            VALUES (
                'x',
                (SELECT id FROM auth.user WHERE username = 'SYSTEM')
            )
    """)
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
