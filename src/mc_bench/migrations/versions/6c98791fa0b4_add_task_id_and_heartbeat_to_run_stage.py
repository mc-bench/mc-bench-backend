"""add_task_id_and_heartbeat_to_run_stage

Revision ID: 6c98791fa0b4
Revises: eb378aad6fd8
Create Date: 2025-03-10 14:15:16.311304

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c98791fa0b4"
down_revision: Union[str, None] = "eb378aad6fd8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "run_stage",
        sa.Column(
            "last_modified",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        schema="specification",
    )
    op.add_column(
        "run_stage",
        sa.Column("task_id", sa.String(length=255), nullable=True),
        schema="specification",
    )
    op.add_column(
        "run_stage",
        sa.Column("heartbeat", sa.TIMESTAMP(), nullable=True),
        schema="specification",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("run_stage", "heartbeat", schema="specification")
    op.drop_column("run_stage", "task_id", schema="specification")
    op.drop_column("run_stage", "last_modified", schema="specification")
    # ### end Alembic commands ###
