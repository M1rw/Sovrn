# =============================================================================
# SOVRN API - Internal Endpoints
# =============================================================================
"""
Internal endpoints for worker communication.
These endpoints are not exposed to external users.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from pydantic import BaseModel
from app.lib import regression_checks

from app.api.v1.deps import get_db
from app.models import Job, Project, SiteGeneration
from app.services.generation import GenerationService
from app.core.config import settings
import structlog

logger = structlog.get_logger()

router = APIRouter()


class ProcessJobRequest(BaseModel):
    job_id: str


class RegressionCheckRequest(BaseModel):
    html: str


class RegressionCheckResponse(BaseModel):
    basic: dict
    accessibility: dict
    failing: list[str]


@router.post("/process-job")
async def process_job(
    request: ProcessJobRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a generation job.
    Called by worker service to run the AI generation pipeline.
    """
    try:
        job_uuid = UUID(request.job_id)
        
        # Get job from database
        result = await db.execute(select(Job).where(Job.id == job_uuid))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get project
        result = await db.execute(select(Project).where(Project.id == job.project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info("Processing job", job_id=str(job_uuid), project_id=str(project.id))
        
        # Initialize generation service
        gen_service = GenerationService(db, settings.INFERENCE_URL)
        
        # Run the generation pipeline based on job type
        if job.type == "full":
            # Run full pipeline: Strategist -> Designer -> Engineer
            result = await gen_service.generate_full(project, job.input)
        elif job.type == "strategy":
            result = await gen_service.generate_strategy(project, job.input)
        elif job.type == "design":
            result = await gen_service.generate_design(project, job.input)
        elif job.type == "engineer":
            result = await gen_service.generate_code(project, job.input)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown job type: {job.type}")
        
        # Create site generation record
        site_gen = SiteGeneration(
            project_id=project.id,
            brief=job.input.get("brief", ""),
            strategy=result.get("strategy", {}),
            design=result.get("design", {}),
            artifacts=result.get("files", {}),
            status="ready"
        )
        db.add(site_gen)
        await db.flush()
        
        # Add generation_id to result
        result["generation_id"] = str(site_gen.id)
        
        logger.info("Job completed successfully", job_id=str(job_uuid), generation_id=str(site_gen.id))
        
        await db.commit()
        
        return {
            "success": True,
            "job_id": str(job_uuid),
            "generation_id": str(site_gen.id),
            "output": result
        }
        
    except Exception as e:
        logger.error("Job processing failed", job_id=str(job_uuid), error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Job processing failed: {str(e)}")


@router.post("/regression-check", response_model=RegressionCheckResponse)
async def regression_check(payload: RegressionCheckRequest):
    """Run lightweight HTML regression heuristics (structure + accessibility)."""
    basic = regression_checks.basic_html_checks(payload.html)
    acc = regression_checks.accessibility_checks(payload.html)
    failing = regression_checks.summarize({**basic, **acc})
    return RegressionCheckResponse(basic=basic, accessibility=acc, failing=failing)
