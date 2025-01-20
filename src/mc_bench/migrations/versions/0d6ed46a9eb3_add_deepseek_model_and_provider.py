"""add_deepseek_model_and_provider

Revision ID: 0d6ed46a9eb3
Revises: 5ca7be2d7150
Create Date: 2025-01-22 15:18:20.990102

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d6ed46a9eb3"
down_revision: Union[str, None] = "5ca7be2d7150"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'DEEPSEEK_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
