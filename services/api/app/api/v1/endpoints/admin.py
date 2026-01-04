# =============================================================================
# SOVRN API - Admin Endpoints
# =============================================================================
"""
Admin-only endpoints for user management, invoice approval, and system monitoring.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import (
    User, Account, Plan, PlanType, SparkLedger, LedgerType,
    Invoice, InvoiceStatus, Job, JobStatus, Project
)
from app.schemas import (
    UserResponse,
    AccountResponse,
    InvoiceResponse,
    ApproveInvoiceRequest,
    TopUpRequest,
    PaginatedResponse,
    MessageResponse,
)
from app.api.v1.deps import get_current_admin


router = APIRouter()


# =============================================================================
# User Management
# =============================================================================

@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)."""
    query = select(User)
    
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginate
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get user details (admin only)."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.account).selectinload(Account.plan))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


@router.post("/users/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Enable/disable user account (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable admin accounts",
        )
    
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    
    return user


# =============================================================================
# Spark Management
# =============================================================================

@router.post("/users/{user_id}/top-up", response_model=AccountResponse)
async def top_up_sparks(
    user_id: UUID,
    request: TopUpRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Add sparks to user account (admin only)."""
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.plan))
        .where(Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    # Create ledger entry
    new_balance = account.sparks_balance + request.amount
    ledger_entry = SparkLedger(
        account_id=account.id,
        type=LedgerType.CREDIT,
        amount=request.amount,
        balance_after=new_balance,
        description=request.description or f"Admin top-up by {admin.email}",
        created_by=admin.id,
    )
    db.add(ledger_entry)
    
    # Update balance (also done by trigger, but explicit here)
    account.sparks_balance = new_balance
    
    await db.commit()
    await db.refresh(account)
    
    return account


# =============================================================================
# Invoice Management
# =============================================================================

@router.get("/invoices", response_model=PaginatedResponse)
async def list_all_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[InvoiceStatus] = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all invoices (admin only)."""
    query = select(Invoice)
    
    if status:
        query = query.where(Invoice.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginate
    query = query.order_by(Invoice.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    return PaginatedResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/invoices/{invoice_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(
    invoice_id: UUID,
    request: ApproveInvoiceRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Approve a pending invoice and credit sparks (admin only)."""
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    
    if invoice.status != InvoiceStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice is not pending. Current status: {invoice.status}",
        )
    
    # Get account
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.plan))
        .where(Account.id == invoice.account_id)
    )
    account = result.scalar_one()
    
    # Update invoice
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = datetime.now(timezone.utc)
    invoice.payment_reference = request.payment_reference
    if request.notes:
        invoice.notes = (invoice.notes or "") + f"\n[Admin] {request.notes}"
    
    # Credit sparks
    new_balance = account.sparks_balance + invoice.sparks_amount
    ledger_entry = SparkLedger(
        account_id=account.id,
        type=LedgerType.CREDIT,
        amount=invoice.sparks_amount,
        balance_after=new_balance,
        description=f"Invoice {invoice.invoice_number} payment",
        reference_id=invoice.id,
        reference_type="invoice",
        created_by=admin.id,
    )
    db.add(ledger_entry)
    
    # Update account balance and plan if applicable
    account.sparks_balance = new_balance
    if invoice.plan_id:
        account.plan_id = invoice.plan_id
        account.plan_started_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


# =============================================================================
# System Stats
# =============================================================================

@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics (admin only)."""
    # User stats
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    active_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )).scalar()
    
    # Project stats
    total_projects = (await db.execute(select(func.count()).select_from(Project))).scalar()
    
    # Job stats
    total_jobs = (await db.execute(select(func.count()).select_from(Job))).scalar()
    completed_jobs = (await db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.COMPLETED)
    )).scalar()
    queued_jobs = (await db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.QUEUED)
    )).scalar()
    
    # Invoice stats
    pending_invoices = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.status == InvoiceStatus.PENDING)
    )).scalar()
    total_revenue = (await db.execute(
        select(func.sum(Invoice.amount_cents))
        .where(Invoice.status == InvoiceStatus.PAID)
    )).scalar() or 0
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
        },
        "projects": {
            "total": total_projects,
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs,
            "queued": queued_jobs,
        },
        "invoices": {
            "pending": pending_invoices,
            "total_revenue_cents": total_revenue,
        }
    }
