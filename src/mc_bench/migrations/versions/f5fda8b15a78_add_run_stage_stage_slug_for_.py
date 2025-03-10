"""add run_stage.stage_slug for polymorphism

Revision ID: f5fda8b15a78
Revises: 665d4b9d70a6
Create Date: 2024-12-09 02:24:05.746839

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5fda8b15a78"
down_revision: Union[str, None] = "665d4b9d70a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "run_stage",
        sa.Column("stage_slug", sa.String(length=255), nullable=False),
        schema="specification",
    )
    op.create_foreign_key(
        None,
        "run_stage",
        "stage",
        ["stage_slug"],
        ["slug"],
        source_schema="specification",
        referent_schema="specification",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "run_stage", schema="specification", type_="foreignkey")
    op.drop_column("run_stage", "stage_slug", schema="specification")
    # ### end Alembic commands ###
