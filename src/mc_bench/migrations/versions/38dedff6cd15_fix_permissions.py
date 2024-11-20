"""Fix permissions

Revision ID: 38dedff6cd15
Revises: 4ce0397c4cf7
Create Date: 2024-11-18 01:21:43.435893

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "38dedff6cd15"
down_revision: Union[str, None] = "4ce0397c4cf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT SELECT, UPDATE, INSERT ON TABLES TO "api";
    GRANT UPDATE ON ALL TABLES IN SCHEMA auth TO api;

    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT SELECT, UPDATE, INSERT ON TABLES TO "admin-api";
    GRANT UPDATE ON ALL TABLES IN SCHEMA specification TO "admin-api";
    """)
    pass


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
