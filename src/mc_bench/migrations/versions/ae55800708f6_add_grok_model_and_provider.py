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


def upgrade() -> None: # This I need to check a bit more 
    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'GROK_SDK'
        ) ON CONFLICT (name) DO NOTHING;

        INSERT INTO specification.model (created_by, slug, active) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'grok-2-1212',
            true
        ) ON CONFLICT (slug) DO NOTHING;

        INSERT INTO specification.provider (
            id,
            created_by,
            model_id,
            provider_class,
            config,
            name,
            is_default
        ) VALUES (
            5,
            (select id from auth.user where username = 'SYSTEM'),
            (select id from specification.model where slug = 'grok-2-1212'),
            'GROK_SDK',
            '{"model": "grok-2-1212", "max_tokens": 131072}',
            'Grok',
            true
        ) ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
