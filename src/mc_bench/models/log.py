from __future__ import annotations

from sqlalchemy.orm import Mapped, relationship

import mc_bench.schema.postgres as schema

from ._base import Base
from .user import User


class LogAction(Base):
    __table__ = schema.research.log_action

    def to_dict(self):
        return {
            "id": self.external_id,
            "created": self.created,
            "name": self.name,
        }


class NoteKind(Base):
    __table__ = schema.research.note_kind


class Note(Base):
    __table__ = schema.research.note
    __mapper_args__ = {
        "polymorphic_on": schema.research.note.c.kind_slug,
        "polymorphic_abstract": True,
    }

    kind: Mapped["NoteKind"] = relationship("NoteKind", lazy="joined")
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[schema.research.note.c.created_by], lazy="joined"
    )

    def to_dict(self):
        return {
            "id": self.external_id,
            "created": self.created,
            "created_by": self.user.username,
            "kind": self.kind.name,
            "content": self.content,
        }


class ObservationlNote(Note):
    __mapper_args__ = {"polymorphic_identity": "OBSERVATION"}


class JustificationNote(Note):
    __mapper_args__ = {"polymorphic_identity": "JUSTIFICATION"}


class Log(Base):
    __table__ = schema.research.log

    __mapper_args__ = {
        "polymorphic_on": schema.research.log.c.action_slug,
        "polymorphic_abstract": True,
    }
    user: Mapped["User"] = relationship("User", lazy="joined")
    action: Mapped["LogAction"] = relationship("LogAction", lazy="joined")
    note: Mapped["Note"] = relationship("Note", lazy="joined")

    sample: Mapped["Sample"] = relationship(  # noqa: F821
        "Sample", secondary=schema.research.sample_log, back_populates="logs"
    )

    template: Mapped["Template"] = relationship(  # noqa: F821
        "Template", secondary=schema.research.template_log, back_populates="logs"
    )

    model: Mapped["Model"] = relationship(  # noqa: F821
        "Model", secondary=schema.research.model_log, back_populates="logs"
    )

    prompt: Mapped["Prompt"] = relationship(  # noqa: F821
        "Prompt", secondary=schema.research.prompt_log, back_populates="logs"
    )

    model_proposal = relationship(
        "ModelExperimentalStateProposal",
        primaryjoin="(Log.id == ModelExperimentalStateProposal.log_id) | (Log.id == ModelExperimentalStateProposal.accepted_log_id) | (Log.id == ModelExperimentalStateProposal.rejected_log_id)",
        viewonly=True,
        uselist=False,
    )

    prompt_proposal = relationship(
        "PromptExperimentalStateProposal",
        primaryjoin="(Log.id == PromptExperimentalStateProposal.log_id) | (Log.id == PromptExperimentalStateProposal.accepted_log_id) | (Log.id == PromptExperimentalStateProposal.rejected_log_id)",
        viewonly=True,
        uselist=False,
    )

    template_proposal = relationship(
        "TemplateExperimentalStateProposal",
        primaryjoin="(Log.id == TemplateExperimentalStateProposal.log_id) | (Log.id == TemplateExperimentalStateProposal.accepted_log_id) | (Log.id == TemplateExperimentalStateProposal.rejected_log_id)",
        viewonly=True,
        uselist=False,
    )

    @property
    def proposal(self):
        return self.model_proposal or self.prompt_proposal or self.template_proposal

    def __init__(self, note: str, user: User, **kwargs):
        super().__init__(user=user, **kwargs)
        self.note = self.NOTE_CLASS(content=note, user=user)

    def to_dict(self, include_proposal=False):
        base_response = {
            "id": self.external_id,
            "kind": self.note.kind.name,
            "created": self.created,
            "action": self.action.name,
            "note": self.note.content,
            "created_by": self.user.username,
        }

        if include_proposal:
            proposal = self.proposal
            if proposal:
                base_response["proposal"] = proposal.to_dict()

        return base_response


class SampleRejection(Log):
    __mapper_args__ = {"polymorphic_identity": "SAMPLE_REJECTION"}
    NOTE_CLASS = JustificationNote


class SampleApproval(Log):
    __mapper_args__ = {"polymorphic_identity": "SAMPLE_APPROVAL"}
    NOTE_CLASS = JustificationNote


class SampleObservation(Log):
    __mapper_args__ = {"polymorphic_identity": "SAMPLE_OBSERVATION"}
    NOTE_CLASS = ObservationlNote


class ExperimentalStateProposal(Log):
    __mapper_args__ = {"polymorphic_identity": "EXPERIMENTAL_STATE_PROPOSAL"}
    NOTE_CLASS = JustificationNote


class ExperimentalStateApproval(Log):
    __mapper_args__ = {"polymorphic_identity": "EXPERIMENTAL_STATE_APPROVAL"}
    NOTE_CLASS = JustificationNote


class ExperimentalStateRejection(Log):
    __mapper_args__ = {"polymorphic_identity": "EXPERIMENTAL_STATE_REJECTION"}
    NOTE_CLASS = JustificationNote


class PromptObservation(Log):
    __mapper_args__ = {"polymorphic_identity": "PROMPT_OBSERVATION"}
    NOTE_CLASS = ObservationlNote


class ModelObservation(Log):
    __mapper_args__ = {"polymorphic_identity": "MODEL_OBSERVATION"}
    NOTE_CLASS = ObservationlNote


class TemplateObservation(Log):
    __mapper_args__ = {"polymorphic_identity": "TEMPLATE_OBSERVATION"}
    NOTE_CLASS = ObservationlNote
