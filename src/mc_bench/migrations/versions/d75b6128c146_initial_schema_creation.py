"""Initial Schema Creation

Revision ID: d75b6128c146
Revises:
Create Date: 2024-11-12 00:21:01.744673

"""

import textwrap
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d75b6128c146"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        textwrap.dedent("""\
    CREATE SCHEMA IF NOT EXISTS auth;
    CREATE SCHEMA IF NOT EXISTS sample;
    CREATE SCHEMA IF NOT EXISTS scoring;
    CREATE SCHEMA IF NOT EXISTS specification;
    """)
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
