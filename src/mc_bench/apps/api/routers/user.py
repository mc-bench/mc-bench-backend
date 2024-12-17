import datetime
from typing import List

import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.apps.api.config import settings
from mc_bench.auth import GithubOauthClient, XAuthClient
from mc_bench.models.user import AuthProvider, AuthProviderEmailHash, User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

user_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)

github_oauth_client = GithubOauthClient(
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    salt=settings.GITHUB_EMAIL_SALT,
)

x_oauth_client = XAuthClient(
    client_id=settings.X_CLIENT_ID,
    client_secret=settings.X_CLIENT_SECRET,
    salt=settings.X_EMAIL_SALT,
    redirect_uri=settings.REDIRECT_URI,
)


class CreateUserRequest(BaseModel):
    username: str


@user_router.get("/api/auth/github")
def github_oauth(code: str, db: Session = Depends(get_managed_session)):
    try:
        access_token = github_oauth_client.get_access_token(code)
        github_user_info = github_oauth_client.get_github_info(
            access_token=access_token
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to login with Github")

    user_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(
            sqlalchemy.and_(
                AuthProviderEmailHash.email_hash.in_(
                    github_user_info["user_email_hashes"]
                )
            )
        )
    )

    registered_emails = list(db.scalars(user_stmt))
    github_provider = db.scalar(
        select(AuthProvider).where(AuthProvider.name == "github")
    )

    if not registered_emails:
        user = User(
            auth_provider_email_hashes=[
                AuthProviderEmailHash(
                    auth_provider=github_provider,
                    email_hash=email_hash,
                    auth_provider_user_id=str(github_user_info["user_id"]),
                )
                for email_hash in github_user_info["user_email_hashes"]
            ]
        )
        db.add(user)
    else:
        user = db.scalar(select(User).where(User.id == registered_emails[0].user_id))
        github_provided_emails = [
            auth_provider_email_hash
            for auth_provider_email_hash in registered_emails
            if auth_provider_email_hash.auth_provider == github_provider
        ]
        existing_hashes = set(
            [email_hash.email_hash for email_hash in github_provided_emails]
        )
        current_hashes = set(github_user_info["user_email_hashes"])
        new_hashes = current_hashes - existing_hashes
        removed_hashes = existing_hashes - current_hashes
        if removed_hashes:
            for github_provided_email in github_provided_emails:
                if github_provided_email.email_hash in removed_hashes:
                    db.delete(github_provided_email)
        if new_hashes:
            new_github_hashes = [
                AuthProviderEmailHash(
                    user=user, auth_provider=github_provider, email_hash=email_hash
                )
                for email_hash in new_hashes
            ]

            db.add_all(new_github_hashes)

    db.flush()
    db.refresh(user)

    user_id = str(user.external_id)

    # Create the access token
    access_token = am.create_access_token(
        data={
            "sub": user_id,
            "scopes": user.scopes,
        },
        expires_delta=datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Create the refresh token
    refresh_token_id, refresh_token = am.create_refresh_token(
        data={
            "sub": user_id,
        },
        expires_delta=datetime.timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": user.username,
    }


@user_router.get("/api/auth/x")
def x_oauth(code: str, db: Session = Depends(get_managed_session)):
    try:
        access_token = x_oauth_client.get_access_token(code)
        x_user_info = x_oauth_client.get_x_info(access_token=access_token)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to login with X")

    user_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(
            sqlalchemy.and_(
                AuthProviderEmailHash.email_hash.in_(
                    x_user_info["user_email_hashes"]
                )
            )
        )
    )

    registered_emails = list(db.scalars(user_stmt))
    x_provider = db.scalar(
        select(AuthProvider).where(AuthProvider.name == "x")
    )

    # If no registered emails, create a new user
    if not registered_emails:
        user = User(
            auth_provider_email_hashes=[
                AuthProviderEmailHash(
                    auth_provider=x_provider,
                    email_hash=email_hash,
                    auth_provider_user_id=str(x_user_info["user_id"]),
                )
                for email_hash in x_user_info["user_email_hashes"]
            ]
        )
        db.add(user)
    else:
        user = db.scalar(select(User).where(User.id == registered_emails[0].user_id))
        x_provided_emails = [
            auth_provider_email_hash
            for auth_provider_email_hash in registered_emails
            if auth_provider_email_hash.auth_provider == x_provider
        ]
        existing_hashes = set(e.email_hash for e in x_provided_emails)
        current_hashes = set(x_user_info["user_email_hashes"])
        new_hashes = current_hashes - existing_hashes
        removed_hashes = existing_hashes - current_hashes

        # Remove old email hashes that no longer appear
        if removed_hashes:
            for x_provided_email in x_provided_emails:
                if x_provided_email.email_hash in removed_hashes:
                    db.delete(x_provided_email)

        # Add any new hashes
        if new_hashes:
            new_x_hashes = [
                AuthProviderEmailHash(
                    user=user, auth_provider=x_provider, email_hash=email_hash
                )
                for email_hash in new_hashes
            ]
            db.add_all(new_x_hashes)

    db.flush()
    db.refresh(user)

    user_id = str(user.external_id)

    # Create the access token
    access_token = am.create_access_token(
        data={
            "sub": user_id,
            "scopes": user.scopes,
        },
        expires_delta=datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Create the refresh token
    refresh_token_id, refresh_token = am.create_refresh_token(
        data={
            "sub": user_id,
        },
        expires_delta=datetime.timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": user.username,
    }


@user_router.get("/api/me")
def read_users_me(
    current_user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    current_scopes: List[str] = Depends(am.current_scopes),
):
    user_stmt = select(User).where(User.external_id == current_user_uuid)
    user = db.scalar(user_stmt)

    if user is None:
        raise HTTPException(
            status_code=404,
        )

    return {"username": user.username, "scopes": current_scopes}


@user_router.post("/api/user")
def create_user(
    payload: CreateUserRequest,
    current_user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    user_stmt = select(User).where(User.external_id == current_user_uuid)

    user = db.scalar(user_stmt)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        user.username = payload.username
    db.add(user)
    db.flush()
    db.refresh(user, attribute_names=["username"])
    return {"username": user.username}


@user_router.post("/api/auth/refresh")
def refresh_token(
    current_user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
):
    # Get user and their scopes from DB
    user_stmt = select(User).where(User.external_id == current_user_uuid)
    user = db.scalar(user_stmt)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Create new access token with scopes from DB
    access_token = am.create_access_token(
        data={
            "sub": current_user_uuid,
            "scopes": user.scopes,
        },
        expires_delta=datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}
