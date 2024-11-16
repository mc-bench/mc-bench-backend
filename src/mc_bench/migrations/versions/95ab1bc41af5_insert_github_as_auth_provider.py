"""Insert github as auth provider

Revision ID: 95ab1bc41af5
Revises: d0abd80553ec
Create Date: 2024-11-15 19:46:00.828244

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "95ab1bc41af5"
down_revision: Union[str, None] = "d0abd80553ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""\
        INSERT INTO auth.user (username) values ('SYSTEM')
        """)
    )

    op.execute(
        sa.text("""\
            INSERT INTO auth.auth_provider (name, created_by)
            VALUES (
                'github',
                (SELECT id FROM auth.user WHERE username = 'SYSTEM')
            )
    """)
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
