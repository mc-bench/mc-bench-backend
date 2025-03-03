"""Add sample tracking, logs, and notes

Revision ID: 91d6a6a71bf0
Revises: 5ca7be2d7150
Create Date: 2025-01-20 00:11:57.255747

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91d6a6a71bf0"
down_revision: Union[str, None] = "0d6ed46a9eb3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA research")

    for role in ["admin-api", "worker", "admin-worker"]:
        op.execute(f"""\
            GRANT USAGE ON SCHEMA research TO "{role}";
            ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA research GRANT SELECT, INSERT, UPDATE ON TABLES TO "{role}";
            ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA research GRANT USAGE ON SEQUENCES TO "{role}";
            ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA research GRANT EXECUTE ON FUNCTIONS TO "{role}";
        """)

    for role in ["api"]:
        op.execute(f"""\
            GRANT USAGE ON SCHEMA research TO "{role}";
            ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA research GRANT SELECT ON TABLES TO "{role}";
        """)

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "log_action",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="research",
        comment="A log action is a reason for making a log entry\n\nA log action has a name.",
    )
    op.create_table(
        "note_kind",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="research",
        comment="A note kind is a type of note, e.g. observation, justification, hypothesis, etc.\n\nA note kind has a name.",
    )
    op.create_table(
        "sample_approval_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="scoring",
    )
    op.create_table(
        "note",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "deleted", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("deleted_by", sa.Integer(), nullable=False),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("kind_slug", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["kind_slug"],
            ["research.note_kind.name"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="research",
        comment="A note is a narrative entry by a person or SYSTEM\n\nA note has a kind, content, and a created timestamp.",
    )
    op.create_table(
        "log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("action_slug", sa.String(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_slug"],
            ["research.log_action.name"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["research.note.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="research",
        comment="A log is an entry indicating an observation or an action\n\nA log has an action and a note.",
    )
    op.add_column(
        "sample",
        sa.Column(
            "is_pending", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        schema="sample",
    )
    op.add_column(
        "sample",
        sa.Column(
            "is_complete", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        schema="sample",
    )
    op.add_column(
        "sample",
        sa.Column("approval_state_id", sa.Integer(), nullable=True),
        schema="sample",
    )
    op.create_foreign_key(
        None,
        "sample",
        "sample_approval_state",
        ["approval_state_id"],
        ["id"],
        source_schema="sample",
        referent_schema="scoring",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "sample", schema="sample", type_="foreignkey")
    op.drop_column("sample", "approval_state_id", schema="sample")
    op.drop_column("sample", "is_complete", schema="sample")
    op.drop_column("sample", "is_pending", schema="sample")
    op.drop_table("log", schema="research")
    op.drop_table("note", schema="research")
    op.drop_table("sample_approval_state", schema="scoring")
    op.drop_table("note_kind", schema="research")
    op.drop_table("log_action", schema="research")
    # ### end Alembic commands ###
