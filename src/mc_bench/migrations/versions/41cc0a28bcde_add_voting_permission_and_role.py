"""Add voting permission and role

Revision ID: 41cc0a28bcde
Revises: 1035a263c03c
Create Date: 2025-02-26 16:56:23.737426

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "41cc0a28bcde"
down_revision: Union[str, None] = "1035a263c03c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


roles_to_permissions = {
    "voter": [
        "voting:vote",
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

    op.execute(
        sa.text(
            """
            INSERT INTO auth.user_role (created_by, user_id, role_id)
            SELECT 
                (SELECT id FROM auth."user" WHERE username = 'SYSTEM'),
                u.id,
                (SELECT id FROM auth."role" WHERE name = 'voter')
            FROM auth."user" u
            WHERE NOT EXISTS (
                SELECT 1
                FROM auth.user_role ur
                WHERE ur.user_id = u.id
                AND ur.role_id = (SELECT id FROM auth."role" WHERE name = 'voter')
            )
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
