from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, object_session, relationship

import mc_bench.schema.postgres as schema

from ._base import Base


class Prompt(Base):
    __table__ = schema.specification.prompt

    author = relationship(
        "User", foreign_keys=[schema.specification.prompt.c.created_by]
    )
    most_recent_editor = relationship(
        "User", foreign_keys=[schema.specification.prompt.c.last_modified_by]
    )

    runs: Mapped[List["Run"]] = relationship(  # noqa: F821
        "Run", uselist=True, back_populates="prompt"
    )

    def to_dict(self, include_runs=False):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.author.username,
            "last_modified": self.last_modified,
            "name": self.name,
            "build_specification": self.build_specification,
            "active": self.active,
            "usage": self.usage,
        }

        if self.most_recent_editor is not None:
            ret["last_modified_by"] = self.most_recent_editor.username
        else:
            ret["last_modified_by"] = None

        if include_runs:
            ret["runs"] = [
                run.to_dict() for run in sorted(self.runs, key=lambda x: x.created)
            ]

        return ret

    @property
    def _usage_expression(self):
        return select(func.count(1)).where(
            schema.specification.run.c.prompt_id == self.id
        )

    @hybrid_property
    def usage(self):
        session = object_session(self)
        return session.scalar(self._usage_expression)

    @usage.expression
    def usage(self):
        return self._usage_expression.scalar_subquery()
