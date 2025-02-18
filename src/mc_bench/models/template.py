import json
from typing import List

import jinja2
from sqlalchemy import func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, object_session, relationship

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

    runs: Mapped[List["Run"]] = relationship(  # noqa: F821
        "Run", uselist=True, back_populates="template"
    )

    def to_dict(self, include_runs=False):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.author.username,
            "last_modified": self.last_modified,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "active": bool(self.active),
            "frozen": bool(self.frozen),
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
            schema.specification.run.c.template_id == self.id
        )

    @hybrid_property
    def usage(self):
        session = object_session(self)
        return session.scalar(self._usage_expression)

    @usage.expression
    def usage(self):
        return self._usage_expression.scalar_subquery()

    def get_default_template_kwargs(self):
        import minecraft_data

        mc_data = minecraft_data.MinecraftDataFiles(
            version=self.minecraft_version,
            game_type=minecraft_data.PC,
        )

        with open(mc_data.get("blocks", "blocks.json"), "r") as f:
            blocks = json.load(f)

        block_types = [block["name"] for block in blocks]

        with open(mc_data.get("biomes", "biomes.json"), "r") as f:
            biomes = json.load(f)

        biome_types = [biome["name"] for biome in biomes]

        return {
            "block_types_list": "\n".join(block_types),
            "biomes_list": "\n".join(biome_types),
            "minecraft_version": self.minecraft_version,
        }

    def render(self, **kwargs):
        render_kwargs = self.get_default_template_kwargs()
        render_kwargs.update(kwargs)
        return jinja2.Template(self.content).render(**render_kwargs)
