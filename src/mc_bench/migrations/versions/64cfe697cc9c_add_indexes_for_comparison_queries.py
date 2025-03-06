"""add_indexes_for_comparison_queries

Revision ID: 64cfe697cc9c
Revises: 7fc9dbcb65bd
Create Date: 2025-03-06 15:58:41.044353

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "64cfe697cc9c"
down_revision: Union[str, None] = "7fc9dbcb65bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Indexes for sample.sample table - critical for comparison batch query
    op.create_index(
        "ix_sample_test_set_approval_state",
        "sample",
        ["test_set_id", "approval_state_id"],
        schema="sample",
    )
    op.create_index(
        "ix_sample_comparison_correlation_id",
        "sample",
        ["comparison_correlation_id"],
        schema="sample",
    )
    op.create_index(
        "ix_sample_comparison_sample_id",
        "sample",
        ["comparison_sample_id"],
        schema="sample",
    )
    op.create_index("ix_sample_external_id", "sample", ["external_id"], schema="sample")

    # 2. Indexes for scoring.comparison table
    op.create_index(
        "ix_comparison_comparison_id", "comparison", ["comparison_id"], schema="scoring"
    )
    op.create_index(
        "ix_comparison_metric_test_set",
        "comparison",
        ["metric_id", "test_set_id"],
        schema="scoring",
    )

    # 3. Indexes for scoring.sample_leaderboard
    op.create_index(
        "ix_sample_leaderboard_metric_test_set",
        "sample_leaderboard",
        ["metric_id", "test_set_id"],
        schema="scoring",
    )
    op.create_index(
        "ix_sample_leaderboard_elo_score",
        "sample_leaderboard",
        ["elo_score"],
        schema="scoring",
    )

    # 4. Indexes for scoring.model_leaderboard
    op.create_index(
        "ix_model_leaderboard_metric_test_set_tag_vote",
        "model_leaderboard",
        ["metric_id", "test_set_id", "tag_id", "vote_count"],
        schema="scoring",
    )
    op.create_index(
        "ix_model_leaderboard_elo_score",
        "model_leaderboard",
        ["elo_score"],
        schema="scoring",
    )

    # 5. Indexes for scoring.prompt_leaderboard
    op.create_index(
        "ix_prompt_leaderboard_metric_test_set_tag_vote",
        "prompt_leaderboard",
        ["metric_id", "test_set_id", "tag_id", "vote_count"],
        schema="scoring",
    )
    op.create_index(
        "ix_prompt_leaderboard_elo_score",
        "prompt_leaderboard",
        ["elo_score"],
        schema="scoring",
    )

    # 6. Indexes for sample.artifact
    op.create_index(
        "ix_artifact_sample_id_kind_id",
        "artifact",
        ["sample_id", "artifact_kind_id"],
        schema="sample",
    )

    # 7. Index for specification.run to optimize joins in sample stats query
    op.create_index(
        "ix_run_model_id_prompt_id",
        "run",
        ["model_id", "prompt_id"],
        schema="specification",
    )

    # 8. Index for scoring.comparison_rank
    op.create_index(
        "ix_comparison_rank_sample_id",
        "comparison_rank",
        ["sample_id"],
        schema="scoring",
    )

    # 9. Create partial index for active approved samples
    # Get the approval state ID directly first
    conn = op.get_bind()
    approval_state_id = conn.execute(
        sa.text("SELECT id FROM scoring.sample_approval_state WHERE name = 'APPROVED'")
    ).scalar()

    if approval_state_id is not None:
        # Create the index with a direct ID value instead of a subquery
        op.execute(
            sa.text(f"""
            CREATE INDEX ix_sample_active_approved
            ON sample.sample (comparison_correlation_id)
            WHERE active = true AND approval_state_id = {approval_state_id}
            """)
        )


def downgrade() -> None:
    # 1. Drop indexes for sample.sample
    op.drop_index(
        "ix_sample_test_set_approval_state", table_name="sample", schema="sample"
    )
    op.drop_index(
        "ix_sample_comparison_correlation_id", table_name="sample", schema="sample"
    )
    op.drop_index(
        "ix_sample_comparison_sample_id", table_name="sample", schema="sample"
    )
    op.drop_index("ix_sample_external_id", table_name="sample", schema="sample")
    op.drop_index("ix_sample_active_approved", table_name="sample", schema="sample")

    # 2. Drop indexes for scoring.comparison
    op.drop_index(
        "ix_comparison_comparison_id", table_name="comparison", schema="scoring"
    )
    op.drop_index(
        "ix_comparison_metric_test_set", table_name="comparison", schema="scoring"
    )

    # 3. Drop indexes for scoring.sample_leaderboard
    op.drop_index(
        "ix_sample_leaderboard_metric_test_set",
        table_name="sample_leaderboard",
        schema="scoring",
    )
    op.drop_index(
        "ix_sample_leaderboard_elo_score",
        table_name="sample_leaderboard",
        schema="scoring",
    )

    # 4. Drop indexes for scoring.model_leaderboard
    op.drop_index(
        "ix_model_leaderboard_metric_test_set_tag_vote",
        table_name="model_leaderboard",
        schema="scoring",
    )
    op.drop_index(
        "ix_model_leaderboard_elo_score",
        table_name="model_leaderboard",
        schema="scoring",
    )

    # 5. Drop indexes for scoring.prompt_leaderboard
    op.drop_index(
        "ix_prompt_leaderboard_metric_test_set_tag_vote",
        table_name="prompt_leaderboard",
        schema="scoring",
    )
    op.drop_index(
        "ix_prompt_leaderboard_elo_score",
        table_name="prompt_leaderboard",
        schema="scoring",
    )

    # 6. Drop indexes for sample.artifact
    op.drop_index(
        "ix_artifact_sample_id_kind_id", table_name="artifact", schema="sample"
    )

    # 7. Drop indexes for specification.run
    op.drop_index("ix_run_model_id_prompt_id", table_name="run", schema="specification")

    # 8. Drop indexes for scoring.comparison_rank
    op.drop_index(
        "ix_comparison_rank_sample_id", table_name="comparison_rank", schema="scoring"
    )
