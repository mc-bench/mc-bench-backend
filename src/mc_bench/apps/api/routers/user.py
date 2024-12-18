import datetime
from typing import List

import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.apps.api.config import settings
from mc_bench.auth.emails import hash_email
from mc_bench.models.user import AuthProvider, AuthProviderEmailHash, User
from mc_bench.server.auth import AuthManager
from mc_bench.util.postgres import get_managed_session

from ..transport_types.requests import CreateUserRequest, LoginRequest, SignupRequest
from ..transport_types.responses import LoginResponse, SignupResponse

user_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


def _validate_username(db: Session, username: str):
    user_stmt = select(sqlalchemy.func.count(User.id)).where(User.username == username)
    user_count = db.scalar(user_stmt)
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Username already taken. If you already have an account, please login instead.",
        )


def _validate_emails(db: Session, emails: List[str]):
    if len(emails) == 0:
        raise HTTPException(
            status_code=400,
            detail="No email found from authentication provider. Please choose a different authentication provider or ensure you have a verified email with the provider.",
        )


def _hash_emails(salt: str, emails: List[str]) -> List[str]:
    return [hash_email(salt, email) for email in emails]


@user_router.post("/api/signup", response_model=SignupResponse)
def signup(request: SignupRequest, db: Session = Depends(get_managed_session)):
    _validate_username(db, request.username)

    auth_provider = db.scalar(
        select(AuthProvider).where(AuthProvider.name == request.signup_auth_provider)
    )
    authentication_payload = auth_provider.get_authentication_payload(
        **request.signup_auth_provider_data
    )

    _validate_emails(authentication_payload.emails)

    hashed_emails = _hash_emails(settings.EMAIL_SALT, authentication_payload.emails)

    user_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(sqlalchemy.and_(AuthProviderEmailHash.email_hash.in_(hashed_emails)))
    )

    registered_emails = list(db.scalars(user_stmt))

    if len(registered_emails) > 0:
        raise HTTPException(
            status_code=400,
            detail="Email already registered. If you already have an account, please login instead.",
        )

    user = User(
        username=request.username,
        auth_provider_email_hashes=[
            AuthProviderEmailHash(
                auth_provider=auth_provider,
                email_hash=email_hash,
                auth_provider_user_id=authentication_payload.user_id,
            )
            for email_hash in authentication_payload.emails
        ],
    )
    db.add(user)
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


@user_router.get("/api/auth/github")
def github_oauth(code: str, db: Session = Depends(get_managed_session)):
    try:
        auth_provider = db.scalar(
            select(AuthProvider).where(AuthProvider.name == "github")
        )
        authentication_payload = auth_provider.get_authentication_payload(code=code)
    except Exception as e:
        print(e)
        import traceback

        print(traceback.format_exc())

        raise HTTPException(status_code=400, detail="Failed to login with Github")

    hashed_emails = _hash_emails(settings.EMAIL_SALT, authentication_payload.emails)

    print(authentication_payload.emails)
    print(hashed_emails)

    user_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(sqlalchemy.and_(AuthProviderEmailHash.email_hash.in_(hashed_emails)))
    )

    registered_emails = list(db.scalars(user_stmt))

    if not registered_emails:
        print("Creating new user")
        user = User(
            auth_provider_email_hashes=[
                AuthProviderEmailHash(
                    auth_provider=auth_provider,
                    email_hash=email_hash,
                    auth_provider_user_id=authentication_payload.user_id,
                )
                for email_hash in hashed_emails
            ]
        )
        db.add(user)
    else:
        print("Updating existing user")
        user = db.scalar(select(User).where(User.id == registered_emails[0].user_id))
        print(user.to_dict())
        provided_emails = [
            auth_provider_email_hash
            for auth_provider_email_hash in registered_emails
            if auth_provider_email_hash.auth_provider == auth_provider
        ]
        existing_hashes = set([email_hash.email_hash for email_hash in provided_emails])
        current_hashes = set(hashed_emails)
        new_hashes = current_hashes - existing_hashes
        removed_hashes = existing_hashes - current_hashes
        if removed_hashes:
            for provided_email in provided_emails:
                if provided_email.email_hash in removed_hashes:
                    db.delete(provided_email)
        if new_hashes:
            new_email_hashes = [
                AuthProviderEmailHash(
                    user=user, auth_provider=auth_provider, email_hash=email_hash
                )
                for email_hash in new_hashes
            ]

            db.add_all(new_email_hashes)

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


@user_router.post("/api/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_managed_session)):
    try:
        auth_provider = db.scalar(
            select(AuthProvider).where(AuthProvider.name == request.login_auth_provider)
        )
        authentication_payload = auth_provider.get_authentication_payload(
            **request.login_auth_provider_data
        )
    except Exception:
        import traceback

        print(traceback.format_exc())
        raise HTTPException(
            status_code=400,
            detail=f"Failed to login with {request.login_auth_provider}",
        )

    hashed_emails = _hash_emails(settings.EMAIL_SALT, authentication_payload.emails)

    user_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(sqlalchemy.and_(AuthProviderEmailHash.email_hash.in_(hashed_emails)))
    )

    registered_emails = list(db.scalars(user_stmt))

    if not registered_emails:
        print("Creating new user")
        user = User(
            auth_provider_email_hashes=[
                AuthProviderEmailHash(
                    auth_provider=auth_provider,
                    email_hash=email_hash,
                    auth_provider_user_id=authentication_payload.user_id,
                )
                for email_hash in hashed_emails
            ]
        )
        db.add(user)
    else:
        print("Updating existing user")
        user = db.scalar(select(User).where(User.id == registered_emails[0].user_id))
        print(user.to_dict())
        provided_emails = [
            auth_provider_email_hash
            for auth_provider_email_hash in registered_emails
            if auth_provider_email_hash.auth_provider == auth_provider
        ]
        existing_hashes = set([email_hash.email_hash for email_hash in provided_emails])
        current_hashes = set(hashed_emails)
        new_hashes = current_hashes - existing_hashes
        removed_hashes = existing_hashes - current_hashes
        if removed_hashes:
            for provided_email in provided_emails:
                if provided_email.email_hash in removed_hashes:
                    db.delete(provided_email)
        if new_hashes:
            new_email_hashes = [
                AuthProviderEmailHash(
                    user=user, auth_provider=auth_provider, email_hash=email_hash
                )
                for email_hash in new_hashes
            ]

            db.add_all(new_email_hashes)

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
