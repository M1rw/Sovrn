# =============================================================================
# SOVRN API - Locale Endpoints
# =============================================================================
"""
Locale and cultural adaptation rules endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import LocaleRule
from app.schemas import LocaleRuleResponse


router = APIRouter()


@router.get("", response_model=list[LocaleRuleResponse])
async def list_locales(
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all supported locales."""
    query = select(LocaleRule).where(LocaleRule.is_active == True)
    
    if region:
        query = query.where(LocaleRule.region == region)
    
    query = query.order_by(LocaleRule.locale, LocaleRule.country_code)
    
    result = await db.execute(query)
    locales = result.scalars().all()
    
    return locales


@router.get("/regions", response_model=list[str])
async def list_regions(
    db: AsyncSession = Depends(get_db)
):
    """List all supported regions."""
    result = await db.execute(
        select(LocaleRule.region)
        .where(LocaleRule.is_active == True, LocaleRule.region.isnot(None))
        .distinct()
        .order_by(LocaleRule.region)
    )
    regions = [row[0] for row in result.all()]
    return regions


@router.get("/{locale}", response_model=LocaleRuleResponse)
async def get_locale(
    locale: str,
    country_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get locale rules for a specific locale."""
    query = select(LocaleRule).where(
        LocaleRule.locale == locale,
        LocaleRule.is_active == True
    )
    
    if country_code:
        query = query.where(LocaleRule.country_code == country_code.upper())
    
    result = await db.execute(query)
    locale_rule = result.scalar_one_or_none()
    
    if not locale_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Locale rules not found for: {locale}",
        )
    
    return locale_rule


@router.get("/{locale}/payment-methods", response_model=list[str])
async def get_payment_methods(
    locale: str,
    country_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get supported payment methods for a locale."""
    query = select(LocaleRule).where(
        LocaleRule.locale == locale,
        LocaleRule.is_active == True
    )
    
    if country_code:
        query = query.where(LocaleRule.country_code == country_code.upper())
    
    result = await db.execute(query)
    locale_rule = result.scalar_one_or_none()
    
    if not locale_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Locale not found: {locale}",
        )
    
    return locale_rule.payment_methods or []
