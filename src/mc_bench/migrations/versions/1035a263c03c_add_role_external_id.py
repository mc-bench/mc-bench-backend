"""Add role external id

Revision ID: 1035a263c03c
Revises: b3bfae61b787
Create Date: 2025-02-26 16:40:23.158203

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1035a263c03c"
down_revision: Union[str, None] = "b3bfae61b787"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "role",
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        schema="auth",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("role", "external_id", schema="auth")
    # ### end Alembic commands ###
