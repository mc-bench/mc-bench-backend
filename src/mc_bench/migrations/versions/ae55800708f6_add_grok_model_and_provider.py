"""add_grok_model_and_provider

Revision ID: ae55800708f6
Revises: d9dbc81fd67d
Create Date: 2025-01-03 18:04:48.996163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae55800708f6'
down_revision: Union[str, None] = 'd9dbc81fd67d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'GROK_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
