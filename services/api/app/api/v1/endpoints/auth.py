# =============================================================================
# SOVRN API - Authentication Endpoints
# =============================================================================
"""
Authentication endpoints: login, register, refresh, logout.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.core.config import settings
from app.models import User, Account, Plan, PlanType
from app.schemas import (
    TokenResponse,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    UserResponse,
    MessageResponse,
)
from app.api.v1.deps import get_current_user


router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    user = User(
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        name=request.name,
        locale=request.locale,
    )
    db.add(user)
    await db.flush()
    
    # Get free plan ID - using raw SQL to avoid enum conversion issues
    result = await db.execute(
        text("SELECT id FROM plans WHERE type = :plan_type"),
        {"plan_type": "free"}
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=500, detail="Free plan not found")
    free_plan_id = row[0]
    
    # Create account with free plan
    account = Account(
        user_id=user.id,
        plan_id=free_plan_id,
        sparks_balance=100,  # Default free plan sparks
    )
    db.add(account)
    await db.commit()
    
    # Generate tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRY_HOURS * 3600,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return tokens."""
    # Find user
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    
    # Generate tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRY_HOURS * 3600,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    token_data = verify_token(request.refresh_token, token_type="refresh")
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Generate new tokens
    access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.JWT_EXPIRY_HOURS * 3600,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user)
):
    """Get current authenticated user info."""
    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    user: User = Depends(get_current_user)
):
    """Logout current user (client should discard tokens)."""
    # In a stateless JWT system, logout is handled client-side
    # For enhanced security, implement token blacklisting with Redis
    return MessageResponse(message="Successfully logged out")
