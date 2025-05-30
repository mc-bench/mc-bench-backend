"""Add metrics

Revision ID: 4d220a984a72
Revises: 9d12f9191c09
Create Date: 2024-11-25 15:26:29.841864

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d220a984a72"
down_revision: Union[str, None] = "9d12f9191c09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

METRICS = [
    {
        "name": "INSTRUCTION_FOLLOWING",
        "description": "How well did the model follow the instructions",
    },
    {
        "name": "UNQUALIFIED_BETTER",
        "description": "Which build is better",
    },
]


def upgrade() -> None:
    for metric in METRICS:
        op.execute(
            sa.text("""\
        INSERT INTO scoring.metric (created_by, name, description) VALUES ((SELECT id FROM auth.user WHERE username = 'SYSTEM'), :name, :description) ON CONFLICT (name) DO NOTHING
        """).bindparams(
                name=metric["name"],
                description=metric["description"],
            )
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
