"""Add sample-reviewer role

Revision ID: 2066aab9985b
Revises: 8b6615c73a4f
Create Date: 2025-01-26 02:46:17.737274

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2066aab9985b"
down_revision: Union[str, None] = "8b6615c73a4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

roles_to_permissions = {
    "sample-reviewer": [
        "sample:read",
        "sample:review",
    ]
}


def upgrade() -> None:
    for role, permissions in roles_to_permissions.items():
        op.execute(
            sa.text("""\
            INSERT INTO auth."role" (
                created_by,
                name
            ) VALUES (
                (SELECT ID FROM auth."user" where username = 'SYSTEM'),
                :role
            )
            ON CONFLICT (name) DO NOTHING;
        """).bindparams(
                role=role,
            )
        )

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
