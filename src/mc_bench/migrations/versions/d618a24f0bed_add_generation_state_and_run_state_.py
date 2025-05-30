"""Add generation_state and run_state states

Revision ID: d618a24f0bed
Revises: 2bd521bcef5d
Create Date: 2024-11-22 14:21:03.972646

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d618a24f0bed"
down_revision: Union[str, None] = "2bd521bcef5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUN_STATES = [
    "CREATED",
    "PROMPT_ENQUEUED",
    "PROMPT_COMPLETED",
    "BUILD_ENQUEUED",
    "BUILD_COMPLETED",
    "POST_PROCESSING_ENQUEUED",
    "POST_PROCESSING_COMPLETED",
    "SAMPLE_PREP_ENQUEUED",
    "COMPLETED",
    "PROMPT_FAILED",
    "BUILD_FAILED",
    "POST_PROCESSING_FAILED",
    "SAMPLE_PREP_FAILED",
]

GENERATION_STATES = [
    "CREATED",
    "IN_PROGRESS",
    "COMPLETED",
    "PARTIAL_FAILED",
    "FAILED",
]


def upgrade() -> None:
    for generation_state in GENERATION_STATES:
        op.execute(
            sa.text("""\
            INSERT INTO specification.generation_state (created_by, slug) VALUES (
                        (SELECT ID FROM auth."user" where username = 'SYSTEM'),
                        :slug
            ) ON CONFLICT (slug) DO NOTHING
        """).bindparams(slug=generation_state)
        )

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
