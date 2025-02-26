"""Add scoped researcher roles

Revision ID: 5f1a3b5bd548
Revises: b241f88ec24a
Create Date: 2025-02-26 13:00:23.081668

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f1a3b5bd548"
down_revision: Union[str, None] = "b241f88ec24a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


roles_to_permissions = {
    "prompt-researcher": [
        "prompt:write",
        "prompt:review",
        "prompt:experiment:propose",
        "generation:write",
        "run:write",
    ],
    "template-researcher": [
        "template:read",
        "template:write",
        "template:review",
        "template:experiment:propose",
        "generation:write",
        "run:write",
    ],
    "model-researcher": [
        "model:read",
        "model:write",
        "model:review",
        "model:experiment:propose",
        "generation:write",
        "run:write",
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
