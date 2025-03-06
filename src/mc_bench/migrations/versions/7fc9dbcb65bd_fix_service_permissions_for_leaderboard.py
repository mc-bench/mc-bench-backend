"""fix_service_permissions_for_leaderboard

Revision ID: 7fc9dbcb65bd
Revises: 188ed0c14a15
Create Date: 2025-03-06 12:54:07.889131

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7fc9dbcb65bd"
down_revision: Union[str, None] = "188ed0c14a15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix permissions for worker role on leaderboard tables
    op.execute("""
    -- Grant worker role permissions on scoring tables
    GRANT SELECT, INSERT, UPDATE ON scoring.model_leaderboard TO "worker";
    GRANT SELECT, INSERT, UPDATE ON scoring.prompt_leaderboard TO "worker";
    GRANT SELECT, INSERT, UPDATE ON scoring.sample_leaderboard TO "worker";
    GRANT SELECT, INSERT, UPDATE ON scoring.processed_comparison TO "worker";
    GRANT SELECT ON scoring.comparison_rank TO "worker";

    -- Grant admin-worker role comprehensive permissions on all scoring tables
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA scoring TO "admin-worker";
    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "admin-worker";

    -- Grant admin-api role permissions to view and manage scoring data
    GRANT SELECT, UPDATE ON scoring.model_leaderboard TO "admin-api";
    GRANT SELECT, UPDATE ON scoring.prompt_leaderboard TO "admin-api";
    GRANT SELECT, UPDATE ON scoring.sample_leaderboard TO "admin-api";
    GRANT SELECT ON scoring.processed_comparison TO "admin-api";
    
    -- Grant api role read permissions on leaderboard tables
    GRANT SELECT ON scoring.model_leaderboard TO "api";
    GRANT SELECT ON scoring.prompt_leaderboard TO "api";
    GRANT SELECT ON scoring.sample_leaderboard TO "api";

    -- Grant usage on sequences in the scoring schema
    GRANT USAGE ON ALL SEQUENCES IN SCHEMA scoring TO "worker";
    GRANT USAGE ON ALL SEQUENCES IN SCHEMA scoring TO "admin-worker";
    GRANT USAGE ON ALL SEQUENCES IN SCHEMA scoring TO "admin-api";
    GRANT USAGE ON ALL SEQUENCES IN SCHEMA scoring TO "api";
    
    -- Default privileges for future sequences
    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring 
    GRANT USAGE ON SEQUENCES TO "worker", "admin-worker", "admin-api", "api";
    """)

    # Add additional permissions for worker role to access required tables
    op.execute("""
    -- Ensure worker has proper access to all tables needed for ELO calculation
    GRANT SELECT ON specification.prompt_tag TO "worker";
    GRANT SELECT ON specification.tag TO "worker";
    GRANT SELECT ON specification.model TO "worker";
    GRANT SELECT ON specification.prompt TO "worker";
    GRANT SELECT ON sample.sample TO "worker";
    GRANT SELECT ON sample.test_set TO "worker";
    GRANT SELECT ON scoring.comparison TO "worker";
    GRANT SELECT ON scoring.metric TO "worker";
    
    -- Add missing permissions for admin-api role
    GRANT SELECT ON specification.prompt_tag TO "admin-api";
    
    -- Add useful default privileges for future tables
    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring 
    GRANT SELECT, INSERT, UPDATE ON TABLES TO "worker";
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
