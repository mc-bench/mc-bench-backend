"""Add proper roles for writing to sample schema

Revision ID: 6d48eca377ff
Revises: e1181f674ab9
Create Date: 2024-11-24 17:13:33.047217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d48eca377ff'
down_revision: Union[str, None] = 'e1181f674ab9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT SELECT, INSERT, UPDATE ON TABLES TO "admin-worker";
    ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT SELECT, INSERT, UPDATE ON TABLES TO "admin-api";
    
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sample TO "admin-worker";
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sample TO "admin-api";
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
