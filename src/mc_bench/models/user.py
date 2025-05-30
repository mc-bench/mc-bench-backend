from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, relationship

import mc_bench.schema.postgres as schema

from ._base import Base


class AuthenticationPayload(BaseModel):
    user_id: str
    username: Optional[str] = None
    emails: List[str]


class Role(Base):
    __table__ = schema.auth.role

    users = relationship(
        "User",
        secondary=schema.auth.user_role,
        primaryjoin=schema.auth.role.c.id == schema.auth.user_role.c.role_id,
        secondaryjoin=schema.auth.user.c.id == schema.auth.user_role.c.user_id,
        viewonly=True,
    )
    permissions = relationship(
        "Permission",
        secondary=schema.auth.role_permission,
        primaryjoin=schema.auth.role.c.id == schema.auth.role_permission.c.role_id,
        secondaryjoin=schema.auth.permission.c.id
        == schema.auth.role_permission.c.permission_id,
        viewonly=True,
    )

    def to_dict(self):
        return {
            "id": self.external_id,
            "name": self.name,
            "permissions": [permission.name for permission in self.permissions],
        }


class UserRole(Base):
    __table__ = schema.auth.user_role
    creator: Mapped["User"] = relationship(
        uselist=False, foreign_keys=[schema.auth.user_role.c.created_by]
    )
    user: Mapped["User"] = relationship(
        uselist=False, foreign_keys=[schema.auth.user_role.c.user_id]
    )
    role: Mapped["Role"] = relationship(
        uselist=False, foreign_keys=[schema.auth.user_role.c.role_id]
    )


class Permission(Base):
    __table__ = schema.auth.permission

    roles = relationship(
        "Role",
        secondary=schema.auth.role_permission,
        primaryjoin=schema.auth.permission.c.id
        == schema.auth.role_permission.c.permission_id,
        secondaryjoin=schema.auth.role.c.id == schema.auth.role_permission.c.role_id,
        viewonly=True,
    )


class UserIdentificationToken(Base):
    __table__ = schema.auth.user_identification_token

    # This can be associated with multiple users (many-to-many)
    users = relationship(
        "User",
        primaryjoin=schema.auth.user_identification_token.c.user_id
        == schema.auth.user.c.id,
        backref="identification_tokens",
        viewonly=False,
    )

    # Users who have this as their canonical token
    canonical_users = relationship(
        "User",
        primaryjoin=schema.auth.user_identification_token.c.id
        == schema.auth.user.c.canonical_identification_token_id,
        backref="canonical_identification_token",
        viewonly=False,
    )


class User(Base):
    __table__ = schema.auth.user

    auth_provider_email_hashes: Mapped[List["AuthProviderEmailHash"]] = relationship(
        uselist=True, back_populates="user"
    )

    roles = relationship(
        "Role",
        secondary=schema.auth.user_role,
        primaryjoin=schema.auth.user.c.id == schema.auth.user_role.c.user_id,
        secondaryjoin=schema.auth.role.c.id == schema.auth.user_role.c.role_id,
        back_populates="users",
    )

    @hybrid_property
    def scopes(self):
        # Flatten the list of permission names from all roles
        return sorted(
            list(
                set(
                    permission.name
                    for role in self.roles
                    for permission in role.permissions
                )
            )
        )

    def to_dict(self):
        return {
            "id": self.external_id,
            "username": self.username,
            "roles": [role.to_dict() for role in self.roles],
            "permissions": self.scopes,
        }


class AuthProviderEmailHash(Base):
    __table__ = schema.auth.auth_provider_email_hash

    user: Mapped["User"] = relationship(
        uselist=False, back_populates="auth_provider_email_hashes"
    )
    auth_provider: Mapped["AuthProvider"] = relationship(uselist=False)


class AuthProvider(Base):
    __table__ = schema.auth.auth_provider
    __mapper_args__ = {"polymorphic_identity": "name"}

    _client_factories = {}

    @classmethod
    def register_client_factory(cls, name, factory):
        cls._client_factories[name] = factory

    @property
    def client(self):
        if not hasattr(self, "_client"):
            factory = self._client_factories.get(self.name)
            if factory:
                self._client = factory()
            else:
                raise RuntimeError(
                    f"No client factory registered for provider type {self.name}"
                )
        return self._client

    def get_access_token(self, code: str) -> str:
        return self.client.get_access_token(code)

    def get_username(self, access_token: str) -> str:
        return self.client.get_username(access_token)

    def get_user_id(self, access_token: str) -> str:
        return str(self.client.get_user_id(access_token))

    def get_emails(self, access_token: str) -> List[str]:
        return self.client.get_user_emails(access_token)

    def get_authentication_payload(self, code: str) -> AuthenticationPayload:
        access_token = self.get_access_token(code)
        return AuthenticationPayload(
            user_id=self.get_user_id(access_token),
            username=self.get_username(access_token),
            emails=self.get_emails(access_token),
        )


class GithubAuthProvider(AuthProvider):
    __mapper_args__ = {"polymorphic_identity": "github"}


class GoogleAuthProvider(AuthProvider):
    __mapper_args__ = {"polymorphic_identity": "google"}
