# =============================================================================
# SOVRN API - Internal Endpoints
# =============================================================================
"""
Internal endpoints for worker communication.
These endpoints are not exposed to external users.
"""

from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel
from app.lib import regression_checks

from app.api.v1.deps import get_db
from app.models import Job, Project, SiteGeneration
from app.services.generation import GenerationService
from app.services.orchestration import (
    GenerationOrchestrator,
    OrchestrationCancelledError,
    OrchestrationContext,
    map_ui_quality_to_target_mode,
    normalize_ui_quality_mode,
    resolve_generation_lane,
    select_aqe_level,
)
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


async def _get_queue_depth(db: AsyncSession) -> int:
    queued_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == "queued")
    )
    return int(queued_result.scalar() or 0)


async def _get_inference_stats() -> dict[str, Any]:
    if not settings.ORCHESTRATION_AQE_ENABLED:
        return {}

    try:
        async with httpx.AsyncClient(
            timeout=settings.ORCHESTRATION_AQE_INFERENCE_STATS_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(f"{settings.INFERENCE_URL.rstrip('/')}/stats")
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning("orchestration_inference_stats_unavailable", error=str(exc))
        return {}


async def _persist_orchestration_progress(
    db: AsyncSession,
    job: Job,
    orchestration_state: dict[str, Any],
) -> None:
    output = job.output if isinstance(job.output, dict) else {}
    output["orchestration"] = orchestration_state
    output["status"] = "processing"
    job.output = output
    await db.commit()


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
        "orchestration": code_output.get("orchestration", {}),
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
    job_uuid: UUID | None = None
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

        job_type = job.type.value if hasattr(job.type, "value") else str(job.type)
        job_input = job.input if isinstance(job.input, dict) else {}
        
        # Run the generation pipeline based on job type
        if job_type == "full" and settings.ORCHESTRATION_RUNTIME_ENABLED:
            queue_depth = await _get_queue_depth(db)
            infer_stats = await _get_inference_stats()

            orchestration_input = job_input.get("orchestration_profile")
            orchestration_payload = (
                orchestration_input
                if isinstance(orchestration_input, dict)
                else {}
            )

            quality_mode = normalize_ui_quality_mode(
                orchestration_payload.get("quality_mode")
                if isinstance(orchestration_payload.get("quality_mode"), str)
                else job_input.get("quality_mode")
            )
            target_mode = map_ui_quality_to_target_mode(quality_mode)
            lane = resolve_generation_lane(quality_mode)
            aqe_level = select_aqe_level(queue_depth=queue_depth, infer_stats=infer_stats)

            async def _progress_callback(orchestration_state: dict[str, Any]) -> None:
                await _persist_orchestration_progress(db=db, job=job, orchestration_state=orchestration_state)

            orchestrator = GenerationOrchestrator(
                OrchestrationContext(
                    db=db,
                    job_id=job.id,
                    generation_service=gen_service,
                    project=project,
                    input_data=job_input,
                    quality_mode=quality_mode,
                    target_mode=target_mode,
                    lane=lane,
                    aqe_level=aqe_level,
                    queue_depth=queue_depth,
                    infer_stats=infer_stats,
                    progress_callback=_progress_callback,
                )
            )

            try:
                result = await orchestrator.run()
            except OrchestrationCancelledError:
                cancellation_output = {
                    "orchestration": orchestrator.state,
                    "status": "cancelled",
                }
                job.output = cancellation_output
                await db.commit()
                logger.info("Job cancelled during orchestration", job_id=str(job_uuid))
                return {
                    "success": False,
                    "cancelled": True,
                    "job_id": str(job_uuid),
                    "output": cancellation_output,
                }
        elif job_type == "full":
            result = await gen_service.generate_full(project, job_input)
        elif job_type == "strategy":
            result = await gen_service.generate_strategy(project, job_input)
        elif job_type == "design":
            result = await gen_service.generate_design(project, job_input)
        elif job_type == "engineer":
            result = await gen_service.generate_code(project, job_input)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown job type: {job_type}")

        if not isinstance(result, dict):
            raise RuntimeError("Generation pipeline returned invalid payload")
        
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
            "orchestration": result.get("orchestration") if isinstance(result, dict) else None,
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
        logger.error(
            "Job processing failed",
            job_id=str(job_uuid) if job_uuid else request.job_id,
            error=str(e),
        )
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Job processing failed: {str(e)}")


@router.post("/regression-check", response_model=RegressionCheckResponse)
async def regression_check(payload: RegressionCheckRequest):
    """Run lightweight HTML regression heuristics (structure + accessibility)."""
    basic = regression_checks.basic_html_checks(payload.html)
    acc = regression_checks.accessibility_checks(payload.html)
    failing = regression_checks.summarize({**basic, **acc})
    return RegressionCheckResponse(basic=basic, accessibility=acc, failing=failing)
