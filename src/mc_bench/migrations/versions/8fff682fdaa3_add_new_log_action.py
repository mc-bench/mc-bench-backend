"""Add new log action

Revision ID: 8fff682fdaa3
Revises: 3491851af8f5
Create Date: 2025-02-25 11:14:25.441110

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8fff682fdaa3"
down_revision: Union[str, None] = "3491851af8f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOG_ACTIONS = [
    "EXPERIMENTAL_STATE_PROPOSAL",
    "EXPERIMENTAL_STATE_APPROVAL",
    "EXPERIMENTAL_STATE_REJECTION",
    "PROMPT_OBSERVATION",
    "MODEL_OBSERVATION",
    "TEMPLATE_OBSERVATION",
]


def upgrade() -> None:
    for log_action in LOG_ACTIONS:
        op.execute(
            sa.text(
                """INSERT INTO research.log_action (name) VALUES (:log_action) ON CONFLICT DO NOTHING"""
            ).bindparams(log_action=log_action)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
