# =============================================================================
# SOVRN API - User Endpoints
# =============================================================================
"""
User management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models import User, Account
from app.schemas import (
    UserResponse,
    UserUpdate,
    UserWithAccount,
    MessageResponse,
)
from app.api.v1.deps import get_current_user


router = APIRouter()


@router.get("/me", response_model=UserWithAccount)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile with account details."""
    # Reload with account relationship
    result = await db.execute(
        select(User)
        .options(selectinload(User.account).selectinload(Account.plan))
        .where(User.id == user.id)
    )
    user = result.scalar_one()
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    update_data = request.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    current_password: str,
    new_password: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user password."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )
    
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    user.password_hash = hash_password(new_password)
    await db.commit()
    
    return MessageResponse(message="Password changed successfully")


@router.delete("/me", response_model=MessageResponse)
async def delete_current_user(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user account (soft delete)."""
    user.is_active = False
    user.email = f"deleted_{user.id}@deleted.local"
    await db.commit()
    
    return MessageResponse(message="Account deleted successfully")
