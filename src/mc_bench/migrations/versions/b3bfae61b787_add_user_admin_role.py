"""Add user-admin role

Revision ID: b3bfae61b787
Revises: a0bb11b95fff
Create Date: 2025-02-26 16:16:50.327726

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3bfae61b787"
down_revision: Union[str, None] = "a0bb11b95fff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


roles_to_permissions = {
    "user-admin": [
        "user:admin",
    ],
}


def upgrade() -> None:
    for role in roles_to_permissions:
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
