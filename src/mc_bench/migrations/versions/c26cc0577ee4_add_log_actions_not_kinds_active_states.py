"""Add log actions, not kinds, active states

Revision ID: c26cc0577ee4
Revises: 91d6a6a71bf0
Create Date: 2025-01-20 00:15:34.576701

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c26cc0577ee4"
down_revision: Union[str, None] = "91d6a6a71bf0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SAMPLE_APPROVAL_STATES = [
    "APPROVED",
    "REJECTED",
]

LOG_ACTIONS = [
    "SAMPLE_REJECTION",
    "SAMPLE_APPROVAL",
    "SAMPLE_OBSERVATION",
]

NOTE_KINDS = [
    "JUSTIFICATION",
    "OBSERVATION",
]


def upgrade() -> None:
    for sample_approval_state in SAMPLE_APPROVAL_STATES:
        op.execute(
            sa.text(
                """INSERT INTO scoring.sample_approval_state (name) VALUES (:sample_approval_state) ON CONFLICT DO NOTHING"""
            ).bindparams(sample_approval_state=sample_approval_state)
        )

    for log_action in LOG_ACTIONS:
        op.execute(
            sa.text(
                """INSERT INTO research.log_action (name) VALUES (:log_action) ON CONFLICT DO NOTHING"""
            ).bindparams(log_action=log_action)
        )

    for note_kind in NOTE_KINDS:
        op.execute(
            sa.text(
                """INSERT INTO research.note_kind (name) VALUES (:note_kind) ON CONFLICT DO NOTHING"""
            ).bindparams(note_kind=note_kind)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
