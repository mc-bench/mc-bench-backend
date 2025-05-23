"""ensure auth.user_role has proper unique constraint

Revision ID: a4bee97b3630
Revises: 7a30bccaa129
Create Date: 2024-11-23 14:10:46.719025

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4bee97b3630"
down_revision: Union[str, None] = "7a30bccaa129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(
        None, "user_role", ["user_id", "role_id"], schema="auth"
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "user_role", schema="auth", type_="unique")
    # ### end Alembic commands ###
