"""insert_google_as_auth_provider

Revision ID: ab2c29f9cc0c
Revises: 8b6615c73a4f
Create Date: 2025-01-27 17:31:03.414851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab2c29f9cc0c'
down_revision: Union[str, None] = '8b6615c73a4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""\
        INSERT INTO auth.auth_provider (name, created_by)
        VALUES ('google', (SELECT id FROM auth.user WHERE username = 'SYSTEM'))
        """)
    )
    pass


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
