# =============================================================================
# SOVRN API - Project Endpoints
# =============================================================================
"""
Project management and site generation endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import User, Project, ProjectStatus, Job, JobType, JobStatus, SiteGeneration
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithGenerations,
    GenerateSiteRequest,
    JobResponse,
    SiteGenerationResponse,
    PaginatedResponse,
    MessageResponse,
)
from app.api.v1.deps import get_current_user, require_sparks
from app.services.generation import GenerationService


router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all projects for current user."""
    query = select(Project).where(Project.user_id == user.id)
    
    if status:
        query = query.where(Project.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginate
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    # Check project limit based on plan
    if user.account and user.account.plan.features.get("max_projects", -1) != -1:
        result = await db.execute(
            select(func.count()).select_from(Project).where(
                Project.user_id == user.id,
                Project.status != ProjectStatus.ARCHIVED
            )
        )
        current_count = result.scalar()
        max_projects = user.account.plan.features.get("max_projects", 1)
        
        if current_count >= max_projects:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Project limit reached. Maximum: {max_projects}",
            )
    
    project = Project(
        user_id=user.id,
        **request.model_dump()
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return project


@router.get("/{project_id}", response_model=ProjectWithGenerations)
async def get_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details with generation history."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.generations))
        .where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project details."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return project


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a project (archive it)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    project.status = ProjectStatus.ARCHIVED
    await db.commit()
    
    return MessageResponse(message="Project archived successfully")


@router.post("/{project_id}/generate", response_model=JobResponse)
async def generate_site(
    project_id: UUID,
    request: GenerateSiteRequest,
    user: User = Depends(require_sparks(1)),
    db: AsyncSession = Depends(get_db)
):
    """Start full site generation for a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Update project with request data
    project.brief = request.brief
    project.locale = request.locale
    project.industry = request.industry
    project.business_type = request.business_type
    project.target_audience = request.target_audience or {}
    project.goals = request.goals or []
    project.settings = request.settings or {}
    project.status = ProjectStatus.GENERATING
    
    # Create generation job
    job = Job(
        project_id=project.id,
        type=JobType.FULL,
        status=JobStatus.QUEUED,
        spark_cost=1,  # Full generation costs 1 spark
        input={
            "brief": request.brief,
            "locale": request.locale,
            "industry": request.industry,
            "business_type": request.business_type,
            "target_audience": request.target_audience,
            "goals": request.goals,
            "template_id": str(request.template_id) if request.template_id else None,
            "settings": request.settings,
        }
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Trigger async generation (worker will pick up the job)
    # In production, this would publish to a job queue
    
    return job


@router.get("/{project_id}/generations", response_model=list[SiteGenerationResponse])
async def list_generations(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all generations for a project."""
    # Verify project ownership
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    result = await db.execute(
        select(SiteGeneration)
        .where(SiteGeneration.project_id == project_id)
        .order_by(SiteGeneration.version.desc())
    )
    generations = result.scalars().all()
    
    return generations


@router.get("/{project_id}/export")
async def export_project(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export project as downloadable ZIP file."""
    # Check export permission
    if user.account and not user.account.plan.features.get("export", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Export not available on your plan. Please upgrade.",
        )
    
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.generations))
        .where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    if project.status != ProjectStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project must be generated before export",
        )
    
    # Generate export (implementation in service)
    # from app.services.export import ExportService
    # return ExportService.create_zip_export(project)
    
    return MessageResponse(message="Export functionality coming soon")
