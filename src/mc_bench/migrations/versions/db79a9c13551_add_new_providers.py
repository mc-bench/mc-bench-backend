"""Add new providers

Revision ID: db79a9c13551
Revises: 514a2c809b29
Create Date: 2025-02-18 07:49:13.060909

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "db79a9c13551"
down_revision: Union[str, None] = "514a2c809b29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'ALIBABA_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)

    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'MISTRAL_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)

    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'ZHIPUAI_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)

    op.execute("""\
        INSERT INTO specification.provider_class (created_by, name) VALUES (
            (select id from auth.user where username = 'SYSTEM'),
            'REKA_SDK'
        ) ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
