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


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("sub")
        exp = payload.get("exp")
        
        if not user_id or not exp:
            return None
        
        return TokenData(
            user_id=user_id,
            expires_at=datetime.fromtimestamp(exp, tz=timezone.utc)
        )
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify a token and check its type."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != token_type:
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
    except JWTError:
        return None
