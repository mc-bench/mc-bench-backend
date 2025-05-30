"""Support render stage

Revision ID: 163167df595b
Revises: ae55800708f6
Create Date: 2025-01-14 13:31:32.278244

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "163167df595b"
down_revision: Union[str, None] = "ae55800708f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAGES = [
    "RENDERING_SAMPLE",
]

ARTIFACT_KINDS = [
    "RENDERED_MODEL_GLB",
]


def upgrade() -> None:
    for stage in STAGES:
        op.execute(
            sa.text(
                """\
                INSERT INTO specification.stage (created_by, slug) values (
                    (SELECT id from auth.user where username = 'SYSTEM'),
                    :slug
                )
                ON CONFLICT (slug) DO NOTHING
            """
            ).bindparams(slug=stage)
        )

    for kind in ARTIFACT_KINDS:
        op.execute(
            sa.text("""\
        INSERT INTO sample.artifact_kind (name) VALUES (:artifact_kind)
        
        """).bindparams(artifact_kind=kind)
        )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
