"""add run states

Revision ID: 848301f47914
Revises: bcaf6ca2021c
Create Date: 2024-12-05 12:00:17.466948

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "848301f47914"
down_revision: Union[str, None] = "bcaf6ca2021c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUN_STATES = [
    "CONTENT_EXPORT_COMPLETE",
    "CONTENT_EXPORT_FAILED",
]


def upgrade() -> None:
    for run_state in RUN_STATES:
        op.execute(
            sa.text("""\
            INSERT INTO specification.run_state (created_by, slug) VALUES (
                        (SELECT ID FROM auth."user" where username = 'SYSTEM'),
                        :slug
            ) ON CONFLICT (slug) DO NOTHING

        """).bindparams(slug=run_state)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
