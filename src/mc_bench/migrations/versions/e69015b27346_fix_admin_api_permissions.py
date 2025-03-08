"""fix_admin_api_permissions

Revision ID: e69015b27346
Revises: 8863c7c9ffd4
Create Date: 2025-03-08 17:01:42.851533

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e69015b27346"
down_revision: Union[str, None] = "8863c7c9ffd4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Grant DELETE permissions to admin-api role for tag management
    op.execute(
        sa.text("""\
        GRANT DELETE ON specification.tag TO "admin-api";
        """)
    )

    # Grant DELETE permissions to admin-api role for model management
    op.execute(
        sa.text("""\
        GRANT DELETE ON specification.model TO "admin-api";
        """)
    )

    # Grant DELETE permissions to admin-api role for prompt management
    op.execute(
        sa.text("""\
        GRANT DELETE ON specification.provider TO "admin-api";
        """)
    )

    # Grant DELETE permissions to admin-api role for prompt management
    op.execute(
        sa.text("""\
        GRANT DELETE ON specification.prompt TO "admin-api";
        """)
    )


    # Grant DELETE permissions to admin-api role for template management
    op.execute(
        sa.text("""\
        GRANT DELETE ON specification.template TO "admin-api";
        """)
    )

    # Grant DELETE permissions for join tables
    op.execute(
        sa.text("""\
        GRANT DELETE ON specification.prompt_tag TO "admin-api";
        """)
    )

    # Add missing UPDATE permissions
    op.execute(
        sa.text("""\
        GRANT UPDATE ON specification.tag TO "admin-api";
        GRANT UPDATE ON specification.model TO "admin-api";
        GRANT UPDATE ON specification.prompt TO "admin-api";
        GRANT UPDATE ON specification.template TO "admin-api";
        """)
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
