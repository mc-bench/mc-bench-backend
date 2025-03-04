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

    logs: Mapped[List["Log"]] = relationship(
        "Log",
        uselist=True,
        secondary=schema.research.model_log,
        back_populates="model",
    )

    experimental_state: Mapped["ExperimentalState"] = relationship(
        "ExperimentalState", lazy="joined"
    )

    proposals: Mapped[List["ModelExperimentalStateProposal"]] = relationship(
        "ModelExperimentalStateProposal",
        uselist=True,
        back_populates="model",
    )

    @property
    def _observational_note_count_expression(self):
        return (
            select(func.count(1))
            .select_from(schema.research.model_log)
            .join(
                schema.research.log,
                schema.research.model_log.c.log_id == schema.research.log.c.id,
            )
            .join(
                schema.research.note,
                schema.research.log.c.note_id == schema.research.note.c.id,
            )
            .where(
                schema.research.model_log.c.model_id == self.id,
                schema.research.note.c.kind_slug == "OBSERVATION",
            )
        )

    @property
    def _pending_proposal_count_expression(self):
        return (
            select(func.count(1))
            .select_from(schema.research.model_experimental_state_proposal)
            .where(
                schema.research.model_experimental_state_proposal.c.model_id == self.id,
                (
                    schema.research.model_experimental_state_proposal.c.accepted.is_(
                        None
                    )
                    | (
                        schema.research.model_experimental_state_proposal.c.accepted
                        == False
                    )
                ),
                (
                    schema.research.model_experimental_state_proposal.c.rejected.is_(
                        None
                    )
                    | (
                        schema.research.model_experimental_state_proposal.c.rejected
                        == False
                    )
                ),
            )
        )

    @hybrid_property
    def observational_note_count(self):
        # Use cached count from the query if available to avoid N+1 queries
        if hasattr(self, "_observational_note_count"):
            return self._observational_note_count

        # Fall back to the database query if necessary
        session = object_session(self)
        return session.scalar(self._observational_note_count_expression)

    @observational_note_count.expression
    def observational_note_count(cls):
        return cls._observational_note_count_expression.scalar_subquery()

    @hybrid_property
    def pending_proposal_count(self):
        # Use cached count from the query if available to avoid N+1 queries
        if hasattr(self, "_pending_proposal_count"):
            return self._pending_proposal_count

        # Fall back to the database query if necessary
        session = object_session(self)
        return session.scalar(self._pending_proposal_count_expression)

    @pending_proposal_count.expression
    def pending_proposal_count(cls):
        return cls._pending_proposal_count_expression.scalar_subquery()

    def to_dict(
        self,
        include_providers=True,
        include_runs=False,
        include_logs=False,
        include_proposals=False,
    ):
        ret = {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.creator.username,
            "last_modified": self.last_modified,
            "slug": self.slug,
            "name": self.name,
            "active": bool(self.active),
            "usage": self.usage,
            "observational_note_count": self.observational_note_count,
            "pending_proposal_count": self.pending_proposal_count,
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

        if include_providers:
            ret["providers"] = [provider.to_dict() for provider in self.providers]

        if include_runs:
            ret["runs"] = [
                run.to_dict() for run in sorted(self.runs, key=lambda x: x.created)
            ]

        if include_proposals:
            ret["proposals"] = [proposal.to_dict() for proposal in self.proposals]

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


class ModelExperimentalStateProposal(Base):
    __table__ = schema.research.model_experimental_state_proposal

    model = relationship(
        "Model",
        back_populates="proposals",
    )

    creator = relationship(
        "User",
        foreign_keys=[schema.research.model_experimental_state_proposal.c.created_by],
    )

    new_experiment_state = relationship(
        "ExperimentalState",
        foreign_keys=[
            schema.research.model_experimental_state_proposal.c.new_experiment_state_id
        ],
    )

    acceptor = relationship(
        "User",
        foreign_keys=[schema.research.model_experimental_state_proposal.c.accepted_by],
    )

    rejector = relationship(
        "User",
        foreign_keys=[schema.research.model_experimental_state_proposal.c.rejected_by],
    )

    log = relationship(
        "Log",
        foreign_keys=[schema.research.model_experimental_state_proposal.c.log_id],
    )

    accepted_log = relationship(
        "Log",
        foreign_keys=[
            schema.research.model_experimental_state_proposal.c.accepted_log_id
        ],
    )

    rejected_log = relationship(
        "Log",
        foreign_keys=[
            schema.research.model_experimental_state_proposal.c.rejected_log_id
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
