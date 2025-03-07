"""Add normalized_username and display_username fields to auth.user

Revision ID: d9dbc81fd67d
Revises: 1eef5895e9f2
Create Date: 2024-12-20 10:49:28.283405

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9dbc81fd67d"
down_revision: Union[str, None] = "1eef5895e9f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "user",
        sa.Column("username_normalized", sa.String(length=64), nullable=True),
        schema="auth",
    )
    op.add_column(
        "user",
        sa.Column("display_username", sa.String(length=64), nullable=True),
        schema="auth",
    )
    op.create_index(
        op.f("ix_auth_user_display_username"),
        "user",
        ["display_username"],
        unique=True,
        schema="auth",
    )
    op.create_index(
        op.f("ix_auth_user_username_normalized"),
        "user",
        ["username_normalized"],
        unique=True,
        schema="auth",
    )
    op.execute(
        "UPDATE auth.user SET username_normalized = LOWER(username), display_username = username WHERE username IS NOT NULL"
    )

    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_auth_user_username_normalized"), table_name="user", schema="auth"
    )
    op.drop_index(
        op.f("ix_auth_user_display_username"), table_name="user", schema="auth"
    )
    op.drop_column("user", "display_username", schema="auth")
    op.drop_column("user", "username_normalized", schema="auth")
    # ### end Alembic commands ###
