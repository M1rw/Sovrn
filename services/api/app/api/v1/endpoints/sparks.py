# =============================================================================
# SOVRN API - Sparks Endpoints
# =============================================================================
"""
Sparks balance and transaction endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import User, Account, SparkLedger, Invoice, InvoiceStatus, Plan, PlanType
from app.schemas import (
    AccountResponse,
    SparkLedgerEntry,
    InvoiceResponse,
    CreateInvoiceRequest,
    PaginatedResponse,
    PlanResponse,
    MessageResponse,
)
from app.api.v1.deps import get_current_user


router = APIRouter()


@router.get("/balance", response_model=AccountResponse)
async def get_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current spark balance and account info."""
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.plan))
        .where(Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    return account


@router.get("/history", response_model=PaginatedResponse)
async def get_spark_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get spark transaction history."""
    # Get account
    result = await db.execute(
        select(Account).where(Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    query = select(SparkLedger).where(SparkLedger.account_id == account.id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginate
    query = query.order_by(SparkLedger.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return PaginatedResponse(
        items=[SparkLedgerEntry.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db)
):
    """List all available plans."""
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.price_cents)
    )
    plans = result.scalars().all()
    return plans


@router.get("/invoices", response_model=PaginatedResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[InvoiceStatus] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user invoices."""
    # Get account
    result = await db.execute(
        select(Account).where(Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    query = select(Invoice).where(Invoice.account_id == account.id)
    
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


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: CreateInvoiceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new invoice for plan purchase."""
    # Get account
    result = await db.execute(
        select(Account).where(Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    # Get plan
    try:
        plan_type = PlanType(request.plan_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan type: {request.plan_type}",
        )
    
    result = await db.execute(
        select(Plan).where(Plan.type == plan_type, Plan.is_active == True)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    
    if plan.price_cents == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create invoice for free plan",
        )
    
    # Check for existing pending invoice
    result = await db.execute(
        select(Invoice).where(
            Invoice.account_id == account.id,
            Invoice.status == InvoiceStatus.PENDING
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending invoice. Please complete or cancel it first.",
        )
    
    # Create invoice (invoice_number is auto-generated by trigger)
    invoice = Invoice(
        account_id=account.id,
        invoice_number="",  # Will be set by trigger
        amount_cents=plan.price_cents,
        currency="USD",
        status=InvoiceStatus.PENDING,
        plan_id=plan.id,
        sparks_amount=plan.sparks_included,
        payment_method=request.payment_method,
        notes=request.notes,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


@router.delete("/invoices/{invoice_id}", response_model=MessageResponse)
async def cancel_invoice(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending invoice."""
    # Get account
    result = await db.execute(
        select(Account).where(Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.account_id == account.id
        )
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
            detail="Only pending invoices can be cancelled",
        )
    
    invoice.status = InvoiceStatus.CANCELLED
    await db.commit()
    
    return MessageResponse(message="Invoice cancelled successfully")
