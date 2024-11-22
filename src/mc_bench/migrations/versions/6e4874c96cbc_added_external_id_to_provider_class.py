"""Added external_id to provider_class

Revision ID: 6e4874c96cbc
Revises: 4085c38e19e8
Create Date: 2024-11-19 22:51:19.701241

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6e4874c96cbc"
down_revision: Union[str, None] = "4085c38e19e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "provider_class",
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        schema="specification",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("provider_class", "external_id", schema="specification")
    # ### end Alembic commands ###