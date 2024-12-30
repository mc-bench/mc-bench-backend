"""Add minecraft_version to template

Revision ID: f1b7837b000d
Revises: 163167df595b
Create Date: 2025-01-15 22:37:33.119661

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1b7837b000d"
down_revision: Union[str, None] = "163167df595b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "template",
        sa.Column("minecraft_version", sa.String(), nullable=True),
        schema="specification",
    )
    op.execute("UPDATE specification.template SET minecraft_version = '1.21.1'")
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("template", "minecraft_version", schema="specification")
    # ### end Alembic commands ###
