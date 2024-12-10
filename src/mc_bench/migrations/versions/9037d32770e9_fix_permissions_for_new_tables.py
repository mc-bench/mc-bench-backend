"""fix permissions for new tables

Revision ID: 9037d32770e9
Revises: f5fda8b15a78
Create Date: 2024-12-10 16:45:32.259956

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9037d32770e9"
down_revision: Union[str, None] = "f5fda8b15a78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT SELECT, INSERT, UPDATE ON TABLES TO "admin-worker";
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA specification TO "admin-worker";
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
