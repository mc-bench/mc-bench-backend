import datetime
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, object_session, relationship

import mc_bench.schema.postgres as schema
from mc_bench.constants import EXPERIMENTAL_STATE

from ._base import Base
from .experimental_state import ExperimentalState
from .log import Log
from .user import User


class Tag(Base):
    __table__ = schema.specification.tag

    prompts: Mapped[List["Prompt"]] = relationship(  # noqa: F821
        "Prompt",
        uselist=True,
        back_populates="tags",
        secondary="specification.prompt_tag",
        viewonly=True,
    )

    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[schema.specification.tag.c.created_by]
    )

    def to_dict(self):
        return {
            "id": self.external_id,
            "name": self.name,
        }


class PromptTag(Base):
    __table__ = schema.specification.prompt_tag

    prompt = relationship(
        "Prompt", foreign_keys=[schema.specification.prompt_tag.c.prompt_id]
    )
    tag = relationship("Tag", foreign_keys=[schema.specification.prompt_tag.c.tag_id])

    creator = relationship(
        "User", foreign_keys=[schema.specification.prompt_tag.c.created_by]
    )


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

    logs: Mapped[List["Log"]] = relationship(
        "Log",
        uselist=True,
        secondary=schema.research.prompt_log,
        back_populates="prompt",
    )

    tags: Mapped[List["Tag"]] = relationship(  # noqa: F821
        "Tag",
        uselist=True,
        back_populates="prompts",
        secondary="specification.prompt_tag",
        viewonly=True,
    )

    proposals: Mapped[List["PromptExperimentalStateProposal"]] = relationship(
        "PromptExperimentalStateProposal",
        uselist=True,
        back_populates="prompt",
        foreign_keys=[schema.research.prompt_experimental_state_proposal.c.prompt_id],
    )

    experimental_state: Mapped["ExperimentalState"] = relationship(
        "ExperimentalState", lazy="joined"
    )

    def add_tag(self, tag: Tag, created_by: User):
        session = object_session(self)
        session.add(PromptTag(prompt=self, tag=tag, creator=created_by))

    def remove_tag(self, tag: Tag):
        session = object_session(self)
        session.query(PromptTag).filter(
            PromptTag.prompt == self, PromptTag.tag == tag
        ).delete()

    def to_dict(self, include_runs=False, include_logs=False, include_proposals=False):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.author.username,
            "last_modified": self.last_modified,
            "name": self.name,
            "build_specification": self.build_specification,
            "build_size": self.build_size,
            "active": self.active,
            "usage": self.usage,
            "tags": [tag.to_dict() for tag in self.tags],
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
            schema.specification.run.c.prompt_id == self.id
        )

    @hybrid_property
    def usage(self):
        session = object_session(self)
        return session.scalar(self._usage_expression)

    @usage.expression
    def usage(self):
        return self._usage_expression.scalar_subquery()


class PromptExperimentalStateProposal(Base):
    __table__ = schema.research.prompt_experimental_state_proposal

    prompt = relationship(
        "Prompt",
        foreign_keys=[schema.research.prompt_experimental_state_proposal.c.prompt_id],
        back_populates="proposals",
    )

    creator = relationship(
        "User",
        foreign_keys=[schema.research.prompt_experimental_state_proposal.c.created_by],
    )

    new_experiment_state = relationship(
        "ExperimentalState",
        foreign_keys=[
            schema.research.prompt_experimental_state_proposal.c.new_experiment_state_id
        ],
    )

    acceptor = relationship(
        "User",
        foreign_keys=[schema.research.prompt_experimental_state_proposal.c.accepted_by],
    )

    rejector = relationship(
        "User",
        foreign_keys=[schema.research.prompt_experimental_state_proposal.c.rejected_by],
    )

    log = relationship(
        "Log",
        foreign_keys=[schema.research.prompt_experimental_state_proposal.c.log_id],
    )

    accepted_log = relationship(
        "Log",
        foreign_keys=[
            schema.research.prompt_experimental_state_proposal.c.accepted_log_id
        ],
    )

    rejected_log = relationship(
        "Log",
        foreign_keys=[
            schema.research.prompt_experimental_state_proposal.c.rejected_log_id
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
