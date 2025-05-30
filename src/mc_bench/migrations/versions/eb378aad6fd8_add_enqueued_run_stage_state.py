"""add_enqueued_run_stage_state

Revision ID: eb378aad6fd8
Revises: e69015b27346
Create Date: 2025-03-10 12:25:25.233461

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eb378aad6fd8"
down_revision: Union[str, None] = "e69015b27346"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ENQUEUED state to run_stage_state table
    op.execute(
        sa.text(
            """\
            INSERT INTO specification.run_stage_state (created_by, slug) values (
                (SELECT id from auth.user where username = 'SYSTEM'),
                :slug
            )
            ON CONFLICT (slug) DO NOTHING
        """
        ).bindparams(slug="ENQUEUED")
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
