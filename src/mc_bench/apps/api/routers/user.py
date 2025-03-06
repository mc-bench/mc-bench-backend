import datetime
from typing import List

import regex
import sqlalchemy
import valx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from mc_bench.apps.api.config import settings
from mc_bench.auth.emails import hash_email
from mc_bench.models.user import (
    AuthProvider,
    AuthProviderEmailHash,
    Role,
    User,
    UserIdentificationToken,
)
from mc_bench.server.auth import AuthManager
from mc_bench.util.logging import get_logger
from mc_bench.util.postgres import get_managed_session

from ..transport_types.requests import CreateUserRequest, LoginRequest, SignupRequest
from ..transport_types.responses import (
    LoginResponse,
    SignupResponse,
    ValidateUsernameResponse,
)

logger = get_logger(__name__)

user_router = APIRouter()

am = AuthManager(
    jwt_secret=settings.JWT_SECRET_KEY,
    jwt_algorithm=settings.ALGORITHM,
)


# TODO: Implement some of this on the frontend
def _validate_username(db: Session, username: str):
    logger.info("Validating username", username=username)

    errors = []

    if len(username.encode("utf-8")) > 64:
        return {
            "is_valid": False,
            "errors": ["Username too long (must be less than 64 characters)."],
        }

    if len(username) == 0:
        return {"is_valid": False, "errors": ["Username cannot be empty."]}

    if not only_has_valid_characters(username):
        errors.append("Username contains invalid characters.")

    split_username = " ".join(regex.split(r"[^a-zA-Z0-9]+", username))

    if result := valx.detect_profanity([split_username], language="All"):
        logger.info("Profanity result", result=result)
        errors.append("Username contains inappropriate words.")

    if result := valx.detect_hate_speech(split_username) != [
        "No Hate and Offensive Speech"
    ]:
        logger.info("Hate speech result", result=result)
        errors.append("Username contains inappropriate content.")

    user_stmt = select(sqlalchemy.func.count(User.id)).where(
        User.username_normalized == username.lower()
    )
    user_count = db.scalar(user_stmt)
    if user_count > 0:
        errors.append("Username already taken.")

    return {"is_valid": len(errors) == 0, "errors": errors}


def _validate_emails(db: Session, emails: List[str]):
    if len(emails) == 0:
        raise HTTPException(
            status_code=400,
            detail="No email found from authentication provider. Please choose a different authentication provider or ensure you have a verified email with the provider.",
        )


def _hash_emails(salt: str, emails: List[str]) -> List[str]:
    return [hash_email(email, salt) for email in emails]


@user_router.post("/api/signup", response_model=SignupResponse)
def signup(request: SignupRequest, db: Session = Depends(get_managed_session)):
    validation_result = _validate_username(db, request.username)
    if not validation_result["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail="\n".join(validation_result["errors"]),
        )

    auth_provider = db.scalar(
        select(AuthProvider).where(AuthProvider.name == request.signup_auth_provider)
    )
    authentication_payload = auth_provider.get_authentication_payload(
        **request.signup_auth_provider_data
    )

    _validate_emails(db, authentication_payload.emails)

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
        username_normalized=request.username.lower(),
        display_username=request.username,
        auth_provider_email_hashes=[
            AuthProviderEmailHash(
                auth_provider=auth_provider,
                email_hash=email_hash,
                auth_provider_user_id=authentication_payload.user_id,
            )
            for email_hash in hashed_emails
        ],
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    if settings.AUTO_GRANT_ADMIN_ROLE:
        role = db.scalar(select(Role).where(Role.name == "admin"))
        user.roles.append(role)
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
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "username": user.username,
    }


# TODO: delete this once this is deployed
@user_router.get("/api/auth/github")
def github_oauth(code: str, db: Session = Depends(get_managed_session)):
    try:
        auth_provider = db.scalar(
            select(AuthProvider).where(AuthProvider.name == "github")
        )
        authentication_payload = auth_provider.get_authentication_payload(code=code)
    except Exception:
        import traceback

        logger.error("Failed to login with Github", error=traceback.format_exc())
        raise HTTPException(status_code=400, detail="Failed to login with Github")

    hashed_emails = _hash_emails(settings.EMAIL_SALT, authentication_payload.emails)

    user_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(sqlalchemy.and_(AuthProviderEmailHash.email_hash.in_(hashed_emails)))
    )

    registered_emails = list(db.scalars(user_stmt))

    if not registered_emails:
        logger.info("Creating new user")
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
        logger.info("Updating existing user")
        user = db.scalar(select(User).where(User.id == registered_emails[0].user_id))
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

        logger.error("Failed to login with Github", error=traceback.format_exc())
        raise HTTPException(
            status_code=400,
            detail=f"Failed to login with {request.login_auth_provider}",
        )

    hashed_emails = _hash_emails(settings.EMAIL_SALT, authentication_payload.emails)
    user_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(AuthProviderEmailHash.email_hash.in_(hashed_emails))
    )

    registered_emails = list(db.scalars(user_stmt))
    emails_associated_with_this_provider = [
        auth_provider_email_hash
        for auth_provider_email_hash in registered_emails
        if auth_provider_email_hash.auth_provider.name == request.login_auth_provider
    ]

    users_associated_with_this_provider = set(
        [email_hash.user.id for email_hash in emails_associated_with_this_provider]
    )

    if len(users_associated_with_this_provider) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple users found for the same email. Please choose a different authentication provider or ensure you only have one account per verified email with the provider.",
        )

    emails_associated_with_another_provider = [
        auth_provider_email_hash
        for auth_provider_email_hash in registered_emails
        if auth_provider_email_hash.auth_provider.name != request.login_auth_provider
    ]

    if (
        not emails_associated_with_this_provider
        + emails_associated_with_another_provider
    ):
        raise HTTPException(
            status_code=400,
            detail="No email found from authentication provider. Please choose a different authentication provider or ensure you have a verified email with the provider.",
        )

    if emails_associated_with_this_provider:
        user_id = emails_associated_with_this_provider[0].user.id
    else:
        user_id = emails_associated_with_another_provider[0].user.id

    user = db.scalar(select(User).where(User.id == user_id))

    provider_emails_stmt = (
        select(AuthProviderEmailHash)
        .join(AuthProvider)
        .where(
            sqlalchemy.and_(
                AuthProvider.name == request.login_auth_provider,
                AuthProviderEmailHash.user_id == user.id,
            )
        )
    )
    provider_emails = list(db.scalars(provider_emails_stmt))

    other_user_emails = [
        auth_provider_email_hash
        for auth_provider_email_hash in emails_associated_with_another_provider
        if auth_provider_email_hash.user.id != user.id
    ]

    other_user_email_hashes = set(
        [email_hash.email_hash for email_hash in other_user_emails]
    )
    existing_hashes = set([email_hash.email_hash for email_hash in provider_emails])

    current_hashes = set(hashed_emails) - other_user_email_hashes
    new_hashes = current_hashes - existing_hashes - other_user_email_hashes
    removed_hashes = existing_hashes - current_hashes

    if removed_hashes:
        for provider_email in provider_emails:
            if provider_email.email_hash in removed_hashes:
                db.delete(provider_email)

    if new_hashes:
        new_email_hashes = [
            AuthProviderEmailHash(
                user=user,
                auth_provider=auth_provider,
                auth_provider_user_id=authentication_payload.user_id,
                email_hash=email_hash,
            )
            for email_hash in new_hashes
        ]

        db.add_all(new_email_hashes)

    db.flush()
    db.refresh(user)

    user_id = str(user.external_id)
    user_name = str(user.username)

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
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "username": user_name,
    }


@user_router.get("/api/me")
def read_users_me(
    request: Request,
    response: Response,
    current_user_uuid: str = Depends(am.get_current_user_uuid),
    db: Session = Depends(get_managed_session),
    current_scopes: List[str] = Depends(am.current_scopes),
):
    # Find the user
    user_stmt = select(User).where(User.external_id == current_user_uuid)
    user = db.scalar(user_stmt)

    # Process session and identification headers
    session_id, identification_token_id = am.process_session_headers(
        request, response, db, user=user
    )

    if user is None:
        raise HTTPException(
            status_code=404,
        )

    # Link identification token to user if it's not already linked
    if identification_token_id:
        identification_token = db.query(UserIdentificationToken).get(
            identification_token_id
        )
        if identification_token and identification_token.user_id is None:
            identification_token.user_id = user.id

            # If user doesn't have a canonical token yet, set this one
            if user.canonical_identification_token_id is None:
                user.canonical_identification_token_id = identification_token.id

            db.flush()

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


@user_router.get("/api/validate-username", response_model=ValidateUsernameResponse)
def validate_username(username: str, db: Session = Depends(get_managed_session)):
    return _validate_username(db, username)


def only_has_valid_characters(username: str) -> bool:
    invalid_chars = regex.compile(r"[^a-zA-Z0-9_\-\p{Extended_Pictographic}]")
    return not bool(invalid_chars.search(username))
