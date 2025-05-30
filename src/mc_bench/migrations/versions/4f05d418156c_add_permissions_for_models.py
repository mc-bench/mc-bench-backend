"""Add permissions for models

Revision ID: 4f05d418156c
Revises: 9f9e88722da4
Create Date: 2024-11-20 13:49:07.526666

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f05d418156c"
down_revision: Union[str, None] = "9f9e88722da4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

roles_to_permissions = {
    "admin": [
        "model:admin",
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
