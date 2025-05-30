"""distribute_approved_samples_to_test_sets

Revision ID: 188ed0c14a15
Revises: 938175add4e2
Create Date: 2025-03-06 11:14:26.241673

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = "188ed0c14a15"
down_revision: Union[str, None] = "938175add4e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Get the IDs of authenticated and unauthenticated test sets
    auth_test_set_id = conn.execute(
        text("SELECT id FROM sample.test_set WHERE name = 'Authenticated Test Set'")
    ).scalar()

    unauth_test_set_id = conn.execute(
        text("SELECT id FROM sample.test_set WHERE name = 'Unauthenticated Test Set'")
    ).scalar()

    if not auth_test_set_id or not unauth_test_set_id:
        print("Warning: One or both test sets not found. Migration skipped.")  # noqa: T201
        return

    # Find approved samples that don't have a test set assigned
    approved_state_id = conn.execute(
        text("SELECT id FROM scoring.sample_approval_state WHERE name = 'APPROVED'")
    ).scalar()

    if not approved_state_id:
        print("Warning: APPROVED state not found. Migration skipped.")  # noqa: T201
        return

    # Get approved samples without a test set
    approved_sample_ids = conn.execute(
        text("""
            SELECT id FROM sample.sample 
            WHERE approval_state_id = :approval_state_id 
            AND (test_set_id IS NULL OR test_set_id = 0)
        """),
        {"approval_state_id": approved_state_id},
    ).fetchall()

    # If no approved samples found, exit gracefully
    if not approved_sample_ids:
        print("No approved samples without test sets found. Migration skipped.")  # noqa: T201
        return

    # Update approximately half of the samples to use authenticated test set
    conn.execute(
        text("""
            UPDATE sample.sample
            SET test_set_id = :test_set_id
            WHERE id IN (
                SELECT id FROM sample.sample 
                WHERE approval_state_id = :approval_state_id 
                AND (test_set_id IS NULL OR test_set_id = 0)
                AND random() < 0.5
            )
        """),
        {"test_set_id": auth_test_set_id, "approval_state_id": approved_state_id},
    )

    # Update remaining samples to use unauthenticated test set
    conn.execute(
        text("""
            UPDATE sample.sample
            SET test_set_id = :test_set_id
            WHERE id IN (
                SELECT id FROM sample.sample 
                WHERE approval_state_id = :approval_state_id 
                AND (test_set_id IS NULL OR test_set_id = 0)
            )
        """),
        {"test_set_id": unauth_test_set_id, "approval_state_id": approved_state_id},
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
