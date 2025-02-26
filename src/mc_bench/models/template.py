import datetime
import json
from typing import List

import jinja2
from sqlalchemy import func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, object_session, relationship

import mc_bench.schema.postgres as schema
from mc_bench.constants import EXPERIMENTAL_STATE

from ._base import Base
from .experimental_state import ExperimentalState
from .log import Log


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

    logs: Mapped[List["Log"]] = relationship(
        "Log",
        uselist=True,
        secondary=schema.research.template_log,
        back_populates="template",
    )

    experimental_state: Mapped["ExperimentalState"] = relationship(
        "ExperimentalState", lazy="joined"
    )

    proposals: Mapped[List["TemplateExperimentalStateProposal"]] = relationship(
        "TemplateExperimentalStateProposal",
        uselist=True,
        back_populates="template",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.template_id
        ],
    )

    def to_dict(self, include_runs=False, include_logs=False, include_proposals=False):
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
            "experimental_state": self.experimental_state.name
            if self.experimental_state
            else EXPERIMENTAL_STATE.EXPERIMENTAL.value,
        }

        if include_logs:
            ret["logs"] = [log.to_dict(include_proposal=True) for log in self.logs]

        if self.most_recent_editor is not None:
            ret["last_modified_by"] = self.most_recent_editor.username
        else:
            ret["last_modified_by"] = None

        if include_runs:
            ret["runs"] = [
                run.to_dict() for run in sorted(self.runs, key=lambda x: x.created)
            ]

        if include_proposals:
            ret["proposals"] = [
                proposal.to_dict(include_logs=True) for proposal in self.proposals
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


class TemplateExperimentalStateProposal(Base):
    __table__ = schema.research.template_experimental_state_proposal

    template = relationship(
        "Template",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.template_id
        ],
    )

    creator = relationship(
        "User",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.created_by
        ],
    )

    new_experiment_state = relationship(
        "ExperimentalState",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.new_experiment_state_id
        ],
    )

    acceptor = relationship(
        "User",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.accepted_by
        ],
    )

    rejector = relationship(
        "User",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.rejected_by
        ],
    )

    log = relationship(
        "Log",
        foreign_keys=[schema.research.template_experimental_state_proposal.c.log_id],
    )

    accepted_log = relationship(
        "Log",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.accepted_log_id
        ],
    )

    rejected_log = relationship(
        "Log",
        foreign_keys=[
            schema.research.template_experimental_state_proposal.c.rejected_log_id
        ],
    )

    def to_dict(self, include_logs=False):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.creator.username,
            "proposed_state": self.new_experiment_state.name,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "accepted_at": self.accepted_at,
            "rejected_at": self.rejected_at,
            "accepted_by": self.acceptor.username if self.acceptor else None,
            "rejected_by": self.rejector.username if self.rejector else None,
        }

        if include_logs:
            ret["log"] = self.log.to_dict() if self.log else None
            ret["accepted_log"] = (
                self.accepted_log.to_dict() if self.accepted_log else None
            )
            ret["rejected_log"] = (
                self.rejected_log.to_dict() if self.rejected_log else None
            )

        return ret

    def approve(self, user, log):
        self.acceptor = user
        self.accepted_at = datetime.datetime.now(datetime.UTC)
        self.accepted = True
        self.accepted_log = log

    def reject(self, user, log):
        self.rejector = user
        self.rejected_at = datetime.datetime.now(datetime.UTC)
        self.rejected = True
        self.rejected_log = log
