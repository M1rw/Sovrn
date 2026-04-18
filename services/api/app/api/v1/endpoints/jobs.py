# =============================================================================
# SOVRN API - Job Endpoints
# =============================================================================
"""
Job management and status endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, Job, JobStatus, Project
from app.schemas import JobResponse, PaginatedResponse
from app.api.v1.deps import get_current_user


router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = None,
    project_id: Optional[UUID] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all jobs for current user."""
    # Build query joining with projects to filter by user
    query = (
        select(Job)
        .join(Project, Job.project_id == Project.id)
        .where(Project.user_id == user.id)
    )
    
    if status:
        query = query.where(Job.status == status)
    
    if project_id:
        query = query.where(Job.project_id == project_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Paginate
    query = query.order_by(Job.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return PaginatedResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job details."""
    result = await db.execute(
        select(Job)
        .join(Project, Job.project_id == Project.id)
        .where(Job.id == job_id, Project.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    return job


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a queued or processing job."""
    result = await db.execute(
        select(Job)
        .join(Project, Job.project_id == Project.id)
        .where(Job.id == job_id, Project.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    if job.status not in [JobStatus.QUEUED, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}",
        )
    
    job.status = JobStatus.CANCELLED
    await db.commit()
    await db.refresh(job)
    
    # Note: Sparks are refunded automatically by worker when job is cancelled
    
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed job."""
    result = await db.execute(
        select(Job)
        .join(Project, Job.project_id == Project.id)
        .where(Job.id == job_id, Project.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed jobs can be retried",
        )
    
    # Create new job with same input
    new_job = Job(
        project_id=job.project_id,
        type=job.type,
        status=JobStatus.QUEUED,
        spark_cost=job.spark_cost,
        priority=job.priority,
        input=job.input,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    
    return new_job
