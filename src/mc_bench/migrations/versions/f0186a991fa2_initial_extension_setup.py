"""Initial Extension Setup

Revision ID: f0186a991fa2
Revises: 1ddb45880af9
Create Date: 2024-11-12 00:53:36.411788

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0186a991fa2"
down_revision: Union[str, None] = "1ddb45880af9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
