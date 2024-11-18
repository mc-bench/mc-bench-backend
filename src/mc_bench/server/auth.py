import functools
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthManager:
    def __init__(self, jwt_secret, jwt_algorithm):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, self.jwt_secret, algorithm=self.jwt_algorithm
        )
        return encoded_jwt

    def get_current_user_uuid(self, token: str = Depends(oauth2_scheme)) -> str:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )
            user_uuid: str = payload.get("sub")
            if user_uuid is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        return user_uuid

    def require_any_scopes(self, scopes):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, token: str = Depends(oauth2_scheme), **kwargs):
                credentials_exception = HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                try:
                    payload = jwt.decode(
                        token,
                        self.jwt_secret,
                        algorithms=[self.jwt_algorithm],
                    )
                    current_scopes: str = payload.get("scopes")
                    if current_scopes is None:
                        raise credentials_exception

                    if set(scopes).isdisjoint(set(current_scopes)):
                        raise credentials_exception

                    return func(*args, **kwargs)

                except JWTError:
                    raise credentials_exception

            return wrapper

        return decorator

    def require_all_scopes(self, scopes):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, token: str = Depends(oauth2_scheme), **kwargs):
                credentials_exception = HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                try:
                    payload = jwt.decode(
                        token,
                        self.jwt_secret,
                        algorithms=[self.jwt_algorithm],
                    )
                    current_scopes: str = payload.get("scopes")
                    if current_scopes is None:
                        raise credentials_exception

                    if not set(scopes).issubset(set(current_scopes)):
                        raise credentials_exception

                    return func(*args, **kwargs)

                except JWTError:
                    raise credentials_exception

            return wrapper

        return decorator

    def current_scopes(self, token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )
            return payload.get("scopes")
        except JWTError:
            raise credentials_exception
