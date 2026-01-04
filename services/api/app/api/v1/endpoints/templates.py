# =============================================================================
# SOVRN API - Template Endpoints
# =============================================================================
"""
Template browsing endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Template
from app.schemas import TemplateResponse, PaginatedResponse


router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    industry: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List available templates."""
    query = select(Template).where(Template.is_active == True)
    
    if category:
        query = query.where(Template.category == category)
    
    if industry:
        query = query.where(Template.industry == industry)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginate
    query = query.order_by(Template.usage_count.desc(), Template.name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return PaginatedResponse(
        items=[TemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/categories", response_model=list[str])
async def list_categories(
    db: AsyncSession = Depends(get_db)
):
    """List all template categories."""
    result = await db.execute(
        select(Template.category)
        .where(Template.is_active == True, Template.category.isnot(None))
        .distinct()
        .order_by(Template.category)
    )
    categories = [row[0] for row in result.all()]
    return categories


@router.get("/industries", response_model=list[str])
async def list_industries(
    db: AsyncSession = Depends(get_db)
):
    """List all template industries."""
    result = await db.execute(
        select(Template.industry)
        .where(Template.is_active == True, Template.industry.isnot(None))
        .distinct()
        .order_by(Template.industry)
    )
    industries = [row[0] for row in result.all()]
    return industries


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get template details."""
    result = await db.execute(
        select(Template).where(Template.id == template_id, Template.is_active == True)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    return template
