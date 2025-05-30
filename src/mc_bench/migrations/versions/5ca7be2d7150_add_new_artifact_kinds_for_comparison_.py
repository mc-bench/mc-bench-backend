"""Add new artifact kinds for comparison artifacts

Revision ID: 5ca7be2d7150
Revises: dfa4bbbc994d
Create Date: 2025-01-16 22:42:24.515955

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ca7be2d7150"
down_revision: Union[str, None] = "dfa4bbbc994d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


KINDS = ["RENDERED_MODEL_GLB_COMPARISON_SAMPLE"]


def upgrade() -> None:
    for kind in KINDS:
        op.execute(
            sa.text("""\
        INSERT INTO sample.artifact_kind (name) VALUES (:artifact_kind)
        
        """).bindparams(artifact_kind=kind)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
