# =============================================================================
# SOVRN API - Internal Endpoints
# =============================================================================
"""
Internal endpoints for worker communication.
These endpoints are not exposed to external users.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
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


def _site_generation_to_output(site_gen: SiteGeneration) -> dict:
    """Reconstruct a canonical generation output payload from persisted fields."""
    files_payload = site_gen.files if isinstance(site_gen.files, list) else []
    files_map: dict[str, str] = {}
    for item in files_payload:
        if isinstance(item, dict):
            path = item.get("path")
            content = item.get("content")
            if isinstance(path, str):
                files_map[path] = content if isinstance(content, str) else ""

    code_output = site_gen.code_output if isinstance(site_gen.code_output, dict) else {}
    return {
        "strategy": site_gen.strategy_output if isinstance(site_gen.strategy_output, dict) else {},
        "design": site_gen.design_output if isinstance(site_gen.design_output, dict) else {},
        "files": files_map,
        "preview_html": code_output.get("preview_html", ""),
        "design_style": code_output.get("design_style"),
        "generation_time_ms": code_output.get("generation_time_ms"),
        "status": code_output.get("status", "completed"),
        "lighthouse_scores": site_gen.lighthouse_scores if isinstance(site_gen.lighthouse_scores, dict) else {},
        "generation_id": str(site_gen.id),
    }


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
        
        # Idempotency guard: once a generation exists for this job, return it.
        existing_generation_result = await db.execute(
            select(SiteGeneration)
            .where(SiteGeneration.job_id == job.id)
            .order_by(SiteGeneration.created_at.desc(), SiteGeneration.id.desc())
            .limit(1)
        )
        existing_generation = existing_generation_result.scalar_one_or_none()
        if existing_generation:
            output = _site_generation_to_output(existing_generation)
            logger.info(
                "Job already persisted, returning existing generation",
                job_id=str(job_uuid),
                generation_id=str(existing_generation.id),
            )
            return {
                "success": True,
                "job_id": str(job_uuid),
                "generation_id": str(existing_generation.id),
                "output": output,
            }

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
        
        # Build persistence payloads that match the SiteGeneration ORM contract.
        strategy_output = result.get("strategy", {}) if isinstance(result, dict) else {}
        design_output = result.get("design", {}) if isinstance(result, dict) else {}

        files_raw = result.get("files", []) if isinstance(result, dict) else []
        if isinstance(files_raw, dict):
            files_payload = [
                {"path": path, "content": content}
                for path, content in files_raw.items()
            ]
        elif isinstance(files_raw, list):
            files_payload = files_raw
        else:
            files_payload = []

        code_output = {
            "preview_html": result.get("preview_html", "") if isinstance(result, dict) else "",
            "design_style": result.get("design_style") if isinstance(result, dict) else None,
            "generation_time_ms": result.get("generation_time_ms") if isinstance(result, dict) else None,
            "status": result.get("status") if isinstance(result, dict) else None,
        }

        version_result = await db.execute(
            select(func.max(SiteGeneration.version)).where(SiteGeneration.project_id == project.id)
        )
        next_version = (version_result.scalar() or 0) + 1

        # Create site generation record
        site_gen = SiteGeneration(
            project_id=project.id,
            job_id=job.id,
            version=next_version,
            strategy_output=strategy_output,
            design_output=design_output,
            code_output=code_output,
            files=files_payload,
            lighthouse_scores=result.get("lighthouse_scores", {}) if isinstance(result, dict) else {},
        )
        db.add(site_gen)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            dedup_result = await db.execute(
                select(SiteGeneration)
                .where(SiteGeneration.job_id == job.id)
                .order_by(SiteGeneration.created_at.desc(), SiteGeneration.id.desc())
                .limit(1)
            )
            dedup_generation = dedup_result.scalar_one_or_none()
            if dedup_generation:
                output = _site_generation_to_output(dedup_generation)
                logger.info(
                    "Duplicate generation insert prevented",
                    job_id=str(job_uuid),
                    generation_id=str(dedup_generation.id),
                )
                return {
                    "success": True,
                    "job_id": str(job_uuid),
                    "generation_id": str(dedup_generation.id),
                    "output": output,
                }
            raise
        
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
