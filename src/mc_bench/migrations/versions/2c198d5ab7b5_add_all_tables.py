"""Add all tables

Revision ID: 2c198d5ab7b5
Revises: f0186a991fa2
Create Date: 2024-11-15 19:34:20.807463

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c198d5ab7b5"
down_revision: Union[str, None] = "f0186a991fa2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="auth",
    )
    op.create_index(
        op.f("ix_auth_user_username"), "user", ["username"], unique=True, schema="auth"
    )
    op.create_table(
        "artifact_kind",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="sample",
    )
    op.create_table(
        "auth_provider",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="auth",
    )
    op.create_table(
        "permission",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="auth",
    )
    op.create_table(
        "role",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="auth",
    )
    op.create_table(
        "metric",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="scoring",
    )
    op.create_table(
        "model",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="specification",
        comment='A reference table of model names, such as "NousResearch/Hermes-3-Llama-3.1-8B" (from hugging face) or "claude-3-5-sonnet-20240620".\n\nWhile some systems may have specific variants, we will mediate any of these differences by recording timestamps and other\nmetadata for how the model was run, accessed, or called.\n\nUnless it becomes necessary, we will generally consider this model name the system under test.',
    )
    op.create_table(
        "prompt",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("build_specification", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="specification",
        comment="A prompt. This will include a template id (which should be the same across every given run).\nThis table is append only. If we choose to use a different template we should make a new prompt row.",
    )
    op.create_table(
        "run_state",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        schema="specification",
    )
    op.create_table(
        "template",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("frozen", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="specification",
    )
    op.create_table(
        "auth_provider_email_hash",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("auth_provider_id", sa.Integer(), nullable=False),
        sa.Column("auth_provider_user_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email_hash", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["auth_provider_id"],
            ["auth.auth_provider.id"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_provider_id", "email_hash"),
        schema="auth",
    )
    op.create_table(
        "user_role",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["auth.role.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="auth",
    )
    op.create_table(
        "run",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("prompt_id", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("state_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["specification.model.id"],
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["specification.prompt.id"],
        ),
        sa.ForeignKeyConstraint(
            ["state_id"],
            ["specification.run_state.id"],
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["specification.template.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="specification",
    )
    op.create_table(
        "artifact",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("artifact_kind_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("bucket", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_kind_id"],
            ["sample.artifact_kind.id"],
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["specification.run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="sample",
    )
    op.create_table(
        "sample",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "external_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("result_inspiration_text", sa.String(), nullable=True),
        sa.Column("result_description_text", sa.String(), nullable=True),
        sa.Column("result_code_text", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["specification.run.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="sample",
    )
    op.create_table(
        "comparison",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "comparison_id",
            sa.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("sample_1_id", sa.Integer(), nullable=False),
        sa.Column("sample_2_id", sa.Integer(), nullable=False),
        sa.Column("winning_sample_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["scoring.metric.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_1_id"],
            ["sample.sample.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_2_id"],
            ["sample.sample.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["winning_sample_id"],
            ["sample.sample.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="scoring",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("comparison", schema="scoring")
    op.drop_table("sample", schema="sample")
    op.drop_table("artifact", schema="sample")
    op.drop_table("run", schema="specification")
    op.drop_table("user_role", schema="auth")
    op.drop_table("auth_provider_email_hash", schema="auth")
    op.drop_table("template", schema="specification")
    op.drop_table("run_state", schema="specification")
    op.drop_table("prompt", schema="specification")
    op.drop_table("model", schema="specification")
    op.drop_table("metric", schema="scoring")
    op.drop_table("role", schema="auth")
    op.drop_table("permission", schema="auth")
    op.drop_table("auth_provider", schema="auth")
    op.drop_table("artifact_kind", schema="sample")
    op.drop_index(op.f("ix_auth_user_username"), table_name="user", schema="auth")
    op.drop_table("user", schema="auth")
    # ### end Alembic commands ###
