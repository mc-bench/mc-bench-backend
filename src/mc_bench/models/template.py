from sqlalchemy import func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import object_session, relationship

import mc_bench.schema.postgres as schema

from ._base import Base


class Template(Base):
    __table__ = schema.specification.template

    author = relationship(
        "User", foreign_keys=[schema.specification.template.c.created_by]
    )
    most_recent_editor = relationship(
        "User", foreign_keys=[schema.specification.template.c.last_modified_by]
    )

    def to_dict(self):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.author.username,
            "last_modified": self.last_modified,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "active": self.active,
            "frozen": self.frozen,
            "usage": self.usage,
        }

        if self.most_recent_editor is not None:
            ret["last_modified_by"] = self.most_recent_editor.username
        else:
            ret["last_modified_by"] = None

        return ret

    @property
    def _usage_expression(self):
        return select(func.count(1)).where(
            schema.specification.run.c.template_id == self.id
        )

    @hybrid_property
    def usage(self):
        session = object_session(self)
        return session.scalar(self._usage_expression)

    @usage.expression
    def usage(self):
        return self._usage_expression.scalar_subquery()
