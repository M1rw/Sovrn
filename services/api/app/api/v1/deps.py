# =============================================================================
# SOVRN API - Authentication Dependencies
# =============================================================================
"""
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import verify_token
from app.models import User, Account


# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    token_data = verify_token(credentials.credentials)
    if not token_data:
        return None
    
    try:
        user_id = UUID(token_data.user_id)
    except ValueError:
        return None
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.account).selectinload(Account.plan))
        .where(User.id == user_id, User.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user or raise 401."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(token_data.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.account).selectinload(Account.plan))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_admin(
    user: User = Depends(get_current_user)
) -> User:
    """Get current user if they are an admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_sparks(minimum: int = 1):
    """Dependency factory to check spark balance."""
    async def check_sparks(user: User = Depends(get_current_user)) -> User:
        if not user.account:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No account found",
            )
        
        # Agency plan has unlimited (-1)
        if user.account.plan.sparks_included == -1:
            return user
        
        if user.account.sparks_balance < minimum:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient sparks. Required: {minimum}, Available: {user.account.sparks_balance}",
            )
        
        return user
    
    return check_sparks
