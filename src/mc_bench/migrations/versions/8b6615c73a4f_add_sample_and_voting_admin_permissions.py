"""Add sample and voting admin permissions

Revision ID: 8b6615c73a4f
Revises: f37ddbc4738c
Create Date: 2025-01-20 22:29:20.630341

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b6615c73a4f"
down_revision: Union[str, None] = "f37ddbc4738c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

roles_to_permissions = {
    "researcher": [
        "sample:read",
        "sample:review",
    ],
    "admin": [
        "sample:admin",
        "voting:admin",
    ],
    "admin-viewer": [
        "sample:read",
    ],
}


def upgrade() -> None:
    for role, permissions in roles_to_permissions.items():
        for permission in permissions:
            op.execute(
                sa.text("""\
                INSERT INTO auth.permission (created_by, name) 
                VALUES (
                    (SELECT ID FROM auth."user" where username = 'SYSTEM'),
                    :permission
                )
                ON CONFLICT (name) DO NOTHING;
            """).bindparams(
                    permission=permission,
                )
            )
            op.execute(
                sa.text("""\
                INSERT INTO auth.role_permission (
                    created_by,
                    role_id,
                    permission_id
                ) VALUES (
                    (SELECT ID FROM auth."user" where username = 'SYSTEM'),
                    (SELECT ID FROM auth."role" where name = :role),
                    (SELECT ID FROM auth."permission" where name = :permission)
                )
                ON CONFLICT (role_id, permission_id) DO NOTHING;
            """).bindparams(
                    role=role,
                    permission=permission,
                )
            )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
