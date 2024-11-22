"""Added is_default to provider table

Revision ID: a0225a967e80
Revises: dbedc0bcab8f
Create Date: 2024-11-20 11:43:11.590909

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0225a967e80"
down_revision: Union[str, None] = "dbedc0bcab8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table_comment("artifact", "", existing_comment=None, schema="sample")
    op.create_table_comment("artifact_kind", "", existing_comment=None, schema="sample")
    op.create_table_comment("sample", "", existing_comment=None, schema="sample")
    op.add_column(
        "provider",
        sa.Column("is_default", sa.Boolean(), nullable=True),
        schema="specification",
    )
    op.create_table_comment("run", "", existing_comment=None, schema="specification")
    op.create_table_comment(
        "run_state", "", existing_comment=None, schema="specification"
    )
    op.create_table_comment(
        "template", "", existing_comment=None, schema="specification"
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table_comment("template", existing_comment="", schema="specification")
    op.drop_table_comment("run_state", existing_comment="", schema="specification")
    op.drop_table_comment("run", existing_comment="", schema="specification")
    op.drop_column("provider", "is_default", schema="specification")
    op.drop_table_comment("sample", existing_comment="", schema="sample")
    op.drop_table_comment("artifact_kind", existing_comment="", schema="sample")
    op.drop_table_comment("artifact", existing_comment="", schema="sample")
    # ### end Alembic commands ###