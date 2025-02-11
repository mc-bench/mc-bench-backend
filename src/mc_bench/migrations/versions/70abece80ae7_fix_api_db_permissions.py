"""Fix API DB Permissions

Revision ID: 70abece80ae7
Revises: 2066aab9985b
Create Date: 2025-02-11 16:38:00.321908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70abece80ae7'
down_revision: Union[str, None] = '2066aab9985b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""\
        GRANT DELETE ON auth.auth_provider_email_hash TO "api";
        """)
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
