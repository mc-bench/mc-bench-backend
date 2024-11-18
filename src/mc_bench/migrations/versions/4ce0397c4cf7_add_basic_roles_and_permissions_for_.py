"""add basic roles and permissions for template management

Revision ID: 4ce0397c4cf7
Revises: 4e797f372395
Create Date: 2024-11-17 22:57:14.921023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ce0397c4cf7'
down_revision: Union[str, None] = '4e797f372395'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

roles_to_permissions = {
    'researcher': [
        "template:read",
        "template:write",
    ],
    "admin": [
        "template:admin",
    ]
}


def upgrade() -> None:
    for role in roles_to_permissions:
        op.execute(sa.text("""\
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
        ))

    for role, permissions in roles_to_permissions.items():
        for permission in permissions:
            op.execute(sa.text("""\
                INSERT INTO auth.permission (created_by, name) 
                VALUES (
                    (SELECT ID FROM auth."user" where username = 'SYSTEM'),
                    :permission
                )
                ON CONFLICT (name) DO NOTHING;
            """).bindparams(
                permission=permission,
            ))
            op.execute(sa.text("""\
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
            ))


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
