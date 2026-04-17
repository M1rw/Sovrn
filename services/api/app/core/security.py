# =============================================================================
# SOVRN API - Security Utilities
# =============================================================================
"""
Authentication, password hashing, and JWT token management.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    exp: datetime
    iat: datetime
    type: str = "access"


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: str
    expires_at: datetime


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access"
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token (longer expiry)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=30)
    
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh"
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_preview_session_token(
    subject: str,
    project_id: str,
    generation_id: str,
    entrypoint: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> tuple[str, datetime]:
    """Create a short-lived JWT token for preview runtime bootstrap."""
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(seconds=settings.PREVIEW_SESSION_TOKEN_TTL_SECONDS)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "preview_session",
        "project_id": str(project_id),
        "generation_id": str(generation_id),
        "entrypoint": entrypoint,
    }

    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, expire


def decode_token_payload(token: str, token_type: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Decode a JWT payload and optionally enforce token type."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None

    if token_type and payload.get("type") != token_type:
        return None

    return payload


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    payload = decode_token_payload(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    exp = payload.get("exp")

    if not user_id or not exp:
        return None

    return TokenData(
        user_id=user_id,
        expires_at=datetime.fromtimestamp(exp, tz=timezone.utc)
    )


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify a token and check its type."""
    payload = decode_token_payload(token, token_type=token_type)
    if not payload:
        return None

    user_id = payload.get("sub")
    exp = payload.get("exp")

    if not user_id or not exp:
        return None

    # Check expiration
    exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
    if exp_datetime < datetime.now(timezone.utc):
        return None

    return TokenData(
        user_id=user_id,
        expires_at=exp_datetime
    )
