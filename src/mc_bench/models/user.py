from typing import List

from sqlalchemy.orm import Mapped, relationship

import mc_bench.schema.postgres as schema

from ._base import Base


class User(Base):
    __table__ = schema.auth.user

    auth_provider_email_hashes: Mapped[List["AuthProviderEmailHash"]] = relationship(
        uselist=True, back_populates="user"
    )


class AuthProviderEmailHash(Base):
    __table__ = schema.auth.auth_provider_email_hash

    user: Mapped["User"] = relationship(
        uselist=False, back_populates="auth_provider_email_hashes"
    )
    auth_provider: Mapped["AuthProvider"] = relationship(uselist=False)


class AuthProvider(Base):
    __table__ = schema.auth.auth_provider
