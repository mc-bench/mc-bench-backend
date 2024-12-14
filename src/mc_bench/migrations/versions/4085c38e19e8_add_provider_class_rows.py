"""Add provider_class rows

Revision ID: 4085c38e19e8
Revises: b097774ba21f
Create Date: 2024-11-19 22:46:00.704472

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4085c38e19e8"
down_revision: Union[str, None] = "b097774ba21f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'OPENAI_SDK'
        ) ON CONFLICT (name) DO NOTHING;

        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'ANTHROPIC_SDK'
        ) ON CONFLICT (name) DO NOTHING;

        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'OPENROUTER_SDK'
        ) ON CONFLICT (name) DO NOTHING;
               
         INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'GEMINI_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
