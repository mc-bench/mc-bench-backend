"""change OpenAI and Gemini provider class

Revision ID: 688482827ae4
Revises: 9037d32770e9
Create Date: 2024-12-13 18:11:51.318675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '688482827ae4'
down_revision: Union[str, None] = '9037d32770e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'GEMINI_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)

def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
