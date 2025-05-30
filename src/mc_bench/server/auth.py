import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from mc_bench.models.user import User, UserIdentificationToken

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Constants for session and identification headers
SESSION_HEADER = "X-MCBench-Session"
IDENTIFICATION_HEADER = "X-MCBench-Identification"


class AuthManager:
    def __init__(self, jwt_secret, jwt_algorithm):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm

    def process_session_headers(
        self,
        request: Request,
        response: Response,
        db: Session = None,
        user: Optional[User] = None,
    ) -> Tuple[uuid.UUID, Optional[int]]:
        """
        Process session and identification headers from the request.
        If they don't exist, generate new ones and set them in the response.

        Args:
            request: The incoming request
            response: The outgoing response
            db: Optional database session for identification token lookup

        Returns:
            Tuple of (session_id: UUID, identification_token_id: Optional[int])
            identification_token_id will be None if no db session was provided
        """
        # Process session ID (must be valid UUID)
        session_id_str = request.headers.get(SESSION_HEADER)
        try:
            if session_id_str:
                session_id = uuid.UUID(session_id_str)
            else:
                session_id = uuid.uuid4()
        except ValueError:
            # Invalid UUID format, generate a new one
            session_id = uuid.uuid4()

        # Set session ID in response
        response.headers[SESSION_HEADER] = str(session_id)

        # Process identification token
        identification_token_id = None
        if db:
            identification_id_str = request.headers.get(IDENTIFICATION_HEADER)
            identification_token = None

            if identification_id_str:
                try:
                    # Try to parse as UUID and look up in database
                    identification_id = uuid.UUID(identification_id_str)
                    identification_token_query = db.query(
                        UserIdentificationToken
                    ).filter(UserIdentificationToken.token == identification_id)

                    if user:
                        identification_token_query = identification_token_query.filter(
                            UserIdentificationToken.user_id == user.id
                        )

                    identification_token = identification_token_query.first()
                except ValueError:
                    # Invalid UUID format, will create new one
                    pass

            # If we don't have a valid token, create one
            if not identification_token:
                new_token_id = uuid.uuid4()
                identification_token = UserIdentificationToken(token=new_token_id)
                if user:
                    identification_token.user_id = user.id
                db.add(identification_token)
                db.flush()  # Get the ID

            # Update last_used_at
            identification_token.last_used_at = datetime.utcnow()

            # Set identification header in response
            response.headers[IDENTIFICATION_HEADER] = str(identification_token.token)
            identification_token_id = identification_token.id

        return session_id, identification_token_id

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=60 * 24 * 7)
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
        def wrapper(token: str = Depends(oauth2_scheme)):
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

            except JWTError:
                raise credentials_exception

        return wrapper

    def require_all_scopes(self, scopes):
        def wrapper(token: str = Depends(oauth2_scheme)):
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

            except JWTError:
                raise credentials_exception

        return wrapper

    def current_scopes(self, token: str = Depends(oauth2_scheme)) -> List[str]:
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

    def is_authenticated(self, token: str = Depends(oauth2_scheme)):
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
            return payload.get("sub")
        except Exception:
            raise credentials_exception

    def maybe_authenticated(self, token: str = Depends(optional_oauth2_scheme)):
        if not token:
            return None

        try:
            return self.is_authenticated(token)
        except Exception:
            return None

    def create_refresh_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=60 * 24 * 7)  # Default to 7 days

        # Add jti (JWT ID) claim for tracking revoked tokens
        token_id = str(uuid.uuid4())
        to_encode.update({"exp": expire, "jti": token_id})

        encoded_jwt = jwt.encode(
            to_encode, self.jwt_secret, algorithm=self.jwt_algorithm
        )
        return token_id, encoded_jwt
