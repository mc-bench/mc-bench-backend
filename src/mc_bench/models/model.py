from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, object_session, relationship

import mc_bench.schema.postgres as schema

from ._base import Base


class Model(Base):
    __table__ = schema.specification.model

    creator = relationship(
        "User", foreign_keys=[schema.specification.model.c.created_by]
    )
    most_recent_editor = relationship(
        "User", foreign_keys=[schema.specification.model.c.last_modified_by]
    )

    providers: Mapped[List["Provider"]] = relationship(  # noqa: F821
        "Provider",
        uselist=True,
        lazy="selectin",
        back_populates="model",
        cascade="all, delete",
        passive_deletes=True,
    )
    runs: Mapped[List["Run"]] = relationship(  # noqa: F821
        "Run", uselist=True, back_populates="model"
    )

    def to_dict(self, include_providers=True, include_runs=False):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.creator.username,
            "last_modified": self.last_modified,
            "slug": self.slug,
            "active": bool(self.active),
            "usage": self.usage,
        }

        if self.most_recent_editor is not None:
            ret["last_modified_by"] = self.most_recent_editor.username
        else:
            ret["last_modified_by"] = None

        if include_providers:
            ret["providers"] = [provider.to_dict() for provider in self.providers]

        if include_runs:
            ret["runs"] = [
                run.to_dict() for run in sorted(self.runs, key=lambda x: x.created)
            ]

        return ret

    @property
    def _usage_expression(self):
        return select(func.count(1)).where(
            schema.specification.run.c.model_id == self.id
        )

    @hybrid_property
    def usage(self):
        session = object_session(self)
        return session.scalar(self._usage_expression)

    @usage.expression
    def usage(self):
        return self._usage_expression.scalar_subquery()

    @property
    def default_provider(self):
        return [provider for provider in self.providers if provider.is_default][0]


class ProviderClass(Base):
    __table__ = schema.specification.provider_class

    def to_dict(self):
        return {
            "id": self.external_id,
            "name": self.name,
        }
