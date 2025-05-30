"""Add default experimental state to existing assets

Revision ID: a0bb11b95fff
Revises: 5f1a3b5bd548
Create Date: 2025-02-26 15:32:53.401649

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0bb11b95fff"
down_revision: Union[str, None] = "5f1a3b5bd548"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""\
        UPDATE specification.model
        SET experimental_state_id = ( SELECT id FROM research.experimental_state WHERE name = 'EXPERIMENTAL' )
        WHERE experimental_state_id IS NULL
    """)

    op.execute("""\
        UPDATE specification.prompt
        SET experimental_state_id = ( SELECT id FROM research.experimental_state WHERE name = 'EXPERIMENTAL' )
        WHERE experimental_state_id IS NULL
    """)

    op.execute("""\
        UPDATE specification.template
        SET experimental_state_id = ( SELECT id FROM research.experimental_state WHERE name = 'EXPERIMENTAL' )
        WHERE experimental_state_id IS NULL
    """)

    op.execute("""\
        UPDATE sample.sample
        SET experimental_state_id = ( SELECT id FROM research.experimental_state WHERE name = 'EXPERIMENTAL' )
        WHERE experimental_state_id IS NULL
    """)


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
