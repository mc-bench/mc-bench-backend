"""Add model, generation, and run permissions

Revision ID: 3bc7893bf74c
Revises: d618a24f0bed
Create Date: 2024-11-22 15:51:45.572665

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3bc7893bf74c"
down_revision: Union[str, None] = "d618a24f0bed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


roles_to_permissions = {
    "researcher": [
        "model:read",
        "model:write",
        "generation:read",
        "run:read",
    ],
    "admin": [
        "generation:admin" "run:admin",
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
