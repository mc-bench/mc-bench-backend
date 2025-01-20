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

    def __init__(self, note: str, user: User, **kwargs):
        super().__init__(user=user, **kwargs)
        self.note = self.NOTE_CLASS(content=note, user=user)

    def to_dict(self):
        return {
            "id": self.external_id,
            "kind": self.note.kind.name,
            "created": self.created,
            "action": self.action.name,
            "note": self.note.content,
            "created_by": self.user.username,
        }


class SampleRejection(Log):
    __mapper_args__ = {"polymorphic_identity": "SAMPLE_REJECTION"}
    NOTE_CLASS = JustificationNote


class SampleApproval(Log):
    __mapper_args__ = {"polymorphic_identity": "SAMPLE_APPROVAL"}
    NOTE_CLASS = JustificationNote


class SampleObservation(Log):
    __mapper_args__ = {"polymorphic_identity": "SAMPLE_OBSERVATION"}
    NOTE_CLASS = ObservationlNote
