"""Add OpenAI Responses provider

Revision ID: 8f8e8c00c1d0
Revises: ffb71aaa0034
Create Date: 2025-01-31 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f8e8c00c1d0"
down_revision: Union[str, None] = "473407e9d86e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'OPENAI_RESPONSES_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""\
        DELETE FROM specification.provider_class 
        WHERE name = 'OPENAI_RESPONSES_SDK';
    """)
