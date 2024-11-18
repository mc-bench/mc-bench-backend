from typing import List

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, relationship

import mc_bench.schema.postgres as schema

from ._base import Base


class Role(Base):
    __table__ = schema.auth.role

    users = relationship(
        "User",
        secondary=schema.auth.user_role,
        primaryjoin=schema.auth.role.c.id == schema.auth.user_role.c.role_id,
        secondaryjoin=schema.auth.user.c.id == schema.auth.user_role.c.user_id,
        back_populates="roles",
    )
    permissions = relationship(
        "Permission",
        secondary=schema.auth.role_permission,
        primaryjoin=schema.auth.role.c.id == schema.auth.role_permission.c.role_id,
        secondaryjoin=schema.auth.permission.c.id
        == schema.auth.role_permission.c.permission_id,
        back_populates="roles",
    )


class Permission(Base):
    __table__ = schema.auth.permission

    roles = relationship(
        "Role",
        secondary=schema.auth.role_permission,
        primaryjoin=schema.auth.permission.c.id
        == schema.auth.role_permission.c.permission_id,
        secondaryjoin=schema.auth.role.c.id == schema.auth.role_permission.c.role_id,
        back_populates="permissions",
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


class AuthProviderEmailHash(Base):
    __table__ = schema.auth.auth_provider_email_hash

    user: Mapped["User"] = relationship(
        uselist=False, back_populates="auth_provider_email_hashes"
    )
    auth_provider: Mapped["AuthProvider"] = relationship(uselist=False)


class AuthProvider(Base):
    __table__ = schema.auth.auth_provider
