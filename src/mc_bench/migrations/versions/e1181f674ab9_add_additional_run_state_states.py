"""Add additional  run_state states

Revision ID: e1181f674ab9
Revises: ab2b7d5586e0
Create Date: 2024-11-24 13:01:06.227978

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1181f674ab9"
down_revision: Union[str, None] = "ab2b7d5586e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUN_STATES = [
    "PROMPT_PROCESSING_ENQUEUED",
    "PROMPT_PROCESSING_COMPLETED",
    "PROMPT_PROCESSING_FAILED",
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
