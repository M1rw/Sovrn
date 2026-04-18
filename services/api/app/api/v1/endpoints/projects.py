# =============================================================================
# SOVRN API - Project Endpoints
# =============================================================================
"""
Project management and site generation endpoints.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_preview_session_token, decode_token_payload
from app.models import User, Project, ProjectStatus, Job, JobType, JobStatus, SiteGeneration
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithGenerations,
    GenerateSiteRequest,
    JobResponse,
    SiteGenerationResponse,
    PreviewArtifactFile,
    PreviewArtifactResponse,
    PreviewSessionRequest,
    PreviewSessionResponse,
    PreviewSessionVerifyRequest,
    PreviewSessionVerifyResponse,
    PatchContractRequest,
    PatchContractApplyRequest,
    PatchContractApplyResponse,
    PatchContractValidationResponse,
    PaginatedResponse,
    MessageResponse,
)
from app.api.v1.deps import bearer_scheme, get_current_user, get_current_user_optional, require_sparks
from app.services.generation import GenerationService
from app.services.patch_contract import resolve_patch_contract_files


router = APIRouter()


def _build_preview_artifact_endpoint(
    project_id: UUID,
    generation_id: UUID,
    entrypoint: str,
) -> str:
    entrypoint_query_value = quote(entrypoint, safe="/")
    return (
        f"/api/v1/projects/{project_id}/preview-artifact"
        f"?generation_id={generation_id}&entrypoint={entrypoint_query_value}"
    )


def _serialize_sse_event(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def _get_project_for_user(
    project_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


async def _get_project(project_id: UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


async def _get_preview_generation(
    project_id: UUID,
    db: AsyncSession,
    generation_id: Optional[UUID] = None,
) -> SiteGeneration:
    query = select(SiteGeneration).where(SiteGeneration.project_id == project_id)

    if generation_id:
        result = await db.execute(query.where(SiteGeneration.id == generation_id))
        generation = result.scalar_one_or_none()
        if not generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation not found for project",
            )
        return generation

    ordered_result = await db.execute(
        query.order_by(SiteGeneration.version.desc(), SiteGeneration.created_at.desc())
    )
    latest_generation = ordered_result.scalars().first()
    if not latest_generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generation artifacts available for project",
        )

    return latest_generation


def _normalize_preview_artifact_files(raw_files: object) -> list[PreviewArtifactFile]:
    if not isinstance(raw_files, list):
        return []

    normalized: list[PreviewArtifactFile] = []
    for file_entry in raw_files:
        if not isinstance(file_entry, dict):
            continue

        path = file_entry.get("path")
        if not isinstance(path, str) or not path.strip():
            continue

        raw_content = file_entry.get("content")
        content = raw_content if isinstance(raw_content, str) else ""

        raw_language = file_entry.get("language")
        language = raw_language if isinstance(raw_language, str) else None

        normalized.append(
            PreviewArtifactFile(
                path=path,
                content=content,
                language=language,
                size_bytes=len(content.encode("utf-8")),
            )
        )

    return normalized


def _select_preview_html(
    files: list[PreviewArtifactFile],
    entrypoint: str,
    code_output: object,
) -> str:
    preferred = next(
        (file.content for file in files if file.path == entrypoint and file.content.strip()),
        None,
    )
    if preferred:
        return preferred

    root_index = next(
        (file.content for file in files if file.path == "index.html" and file.content.strip()),
        None,
    )
    if root_index:
        return root_index

    nested_index = next(
        (file.content for file in files if file.path.endswith("/index.html") and file.content.strip()),
        None,
    )
    if nested_index:
        return nested_index

    if isinstance(code_output, dict):
        fallback_preview = code_output.get("preview_html")
        if isinstance(fallback_preview, str) and fallback_preview.strip():
            return fallback_preview

    return ""


def _decode_preview_session_claims(token: str) -> Optional[dict[str, Any]]:
    payload = decode_token_payload(token, token_type="preview_session")
    if not payload:
        return None

    required_fields = ("project_id", "generation_id", "entrypoint", "exp")
    for field_name in required_fields:
        if field_name not in payload:
            return None

    if not isinstance(payload.get("project_id"), str):
        return None
    if not isinstance(payload.get("generation_id"), str):
        return None
    if not isinstance(payload.get("entrypoint"), str):
        return None

    return payload


def _resolve_preview_session_access(
    payload: dict[str, Any],
    project_id: UUID,
    generation_id: Optional[UUID],
    entrypoint: str,
) -> tuple[UUID, str, datetime]:
    try:
        claimed_project_id = UUID(str(payload["project_id"]))
        claimed_generation_id = UUID(str(payload["generation_id"]))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid preview session token claims",
        )

    if claimed_project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Preview session token is not valid for project",
        )

    if generation_id and generation_id != claimed_generation_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Preview session token is not valid for generation",
        )

    claimed_entrypoint = str(payload["entrypoint"]).strip() or "index.html"
    requested_entrypoint = entrypoint.strip() or claimed_entrypoint
    if requested_entrypoint != claimed_entrypoint:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Preview session token is not valid for entrypoint",
        )

    raw_exp = payload.get("exp")
    if not isinstance(raw_exp, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid preview session token expiry",
        )

    expires_at = datetime.fromtimestamp(raw_exp, tz=timezone.utc)
    return (generation_id or claimed_generation_id, requested_entrypoint, expires_at)


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


@router.get("/{project_id}/preview-artifact", response_model=PreviewArtifactResponse)
async def get_preview_artifact(
    project_id: UUID,
    generation_id: Optional[UUID] = Query(default=None),
    entrypoint: str = Query(default="index.html", min_length=1, max_length=260),
    user: Optional[User] = Depends(get_current_user_optional),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Get normalized generation files for browser preview runtime mounting."""
    resolved_generation_id = generation_id
    resolved_entrypoint = entrypoint.strip() or "index.html"

    if user is not None:
        project = await _get_project_for_user(project_id=project_id, user_id=user.id, db=db)
    else:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = _decode_preview_session_claims(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid preview session token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        resolved_generation_id, resolved_entrypoint, _ = _resolve_preview_session_access(
            payload=payload,
            project_id=project_id,
            generation_id=generation_id,
            entrypoint=resolved_entrypoint,
        )
        project = await _get_project(project_id=project_id, db=db)

    generation = await _get_preview_generation(
        project_id=project.id,
        db=db,
        generation_id=resolved_generation_id,
    )

    normalized_files = _normalize_preview_artifact_files(generation.files)
    preview_html = _select_preview_html(
        files=normalized_files,
        entrypoint=resolved_entrypoint,
        code_output=generation.code_output,
    )

    if not preview_html:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preview HTML available for generation artifacts",
        )

    return PreviewArtifactResponse(
        project_id=project.id,
        generation_id=generation.id,
        generation_version=max(generation.version, 1),
        entrypoint=resolved_entrypoint,
        preview_html=preview_html,
        files=normalized_files,
        source="site_generation",
    )


@router.post("/{project_id}/preview-session", response_model=PreviewSessionResponse)
async def create_preview_session(
    project_id: UUID,
    request: PreviewSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue a signed token for preview runtime bootstrap and artifact retrieval."""
    project = await _get_project_for_user(project_id=project_id, user_id=user.id, db=db)
    generation = await _get_preview_generation(
        project_id=project.id,
        db=db,
        generation_id=request.generation_id,
    )

    requested_ttl = request.ttl_seconds or settings.PREVIEW_SESSION_TOKEN_TTL_SECONDS
    ttl_seconds = max(60, min(requested_ttl, settings.PREVIEW_SESSION_TOKEN_MAX_TTL_SECONDS))
    resolved_entrypoint = request.entrypoint.strip() or "index.html"

    token, expires_at = create_preview_session_token(
        subject=str(user.id),
        project_id=str(project.id),
        generation_id=str(generation.id),
        entrypoint=resolved_entrypoint,
        expires_delta=timedelta(seconds=ttl_seconds),
        additional_claims={"scope": "preview_runtime_bootstrap"},
    )

    artifact_endpoint = _build_preview_artifact_endpoint(
        project_id=project.id,
        generation_id=generation.id,
        entrypoint=resolved_entrypoint,
    )

    return PreviewSessionResponse(
        token=token,
        expires_at=expires_at,
        project_id=project.id,
        generation_id=generation.id,
        entrypoint=resolved_entrypoint,
        artifact_endpoint=artifact_endpoint,
    )


@router.post("/{project_id}/preview-session/verify", response_model=PreviewSessionVerifyResponse)
async def verify_preview_session(
    project_id: UUID,
    request: PreviewSessionVerifyRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Verify preview-session token claims for secure runtime bootstrap handshakes."""
    if user is not None:
        await _get_project_for_user(project_id=project_id, user_id=user.id, db=db)
    else:
        await _get_project(project_id=project_id, db=db)

    payload = _decode_preview_session_claims(request.token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid preview session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    requested_entrypoint = request.entrypoint or ""
    resolved_generation_id, resolved_entrypoint, expires_at = _resolve_preview_session_access(
        payload=payload,
        project_id=project_id,
        generation_id=request.generation_id,
        entrypoint=requested_entrypoint,
    )

    artifact_endpoint = _build_preview_artifact_endpoint(
        project_id=project_id,
        generation_id=resolved_generation_id,
        entrypoint=resolved_entrypoint,
    )

    return PreviewSessionVerifyResponse(
        valid=True,
        project_id=project_id,
        generation_id=resolved_generation_id,
        entrypoint=resolved_entrypoint,
        expires_at=expires_at,
        artifact_endpoint=artifact_endpoint,
    )


@router.post("/{project_id}/patch-contract/validate", response_model=PatchContractValidationResponse)
async def validate_patch_contract(
    project_id: UUID,
    request: PatchContractRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate Phase 3 deterministic patch contract payloads before apply."""
    await _get_project_for_user(project_id=project_id, user_id=user.id, db=db)

    if request.project_id and request.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patch contract project_id does not match request path",
        )

    files_touched = sorted({operation.path for operation in request.operations})

    return PatchContractValidationResponse(
        valid=True,
        project_id=project_id,
        generation_id=request.generation_id,
        version=request.version,
        operation_count=len(request.operations),
        files_touched=files_touched,
        fallback_mode=request.fallback_mode,
    )


@router.post("/{project_id}/patch-contract/resolve", response_model=PatchContractApplyResponse)
async def resolve_patch_contract(
    project_id: UUID,
    request: PatchContractApplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve patch-contract operations with conflict and rollback handling."""
    await _get_project_for_user(project_id=project_id, user_id=user.id, db=db)

    if request.contract.project_id and request.contract.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patch contract project_id does not match request path",
        )

    resolution = resolve_patch_contract_files(request.files, request.contract)

    return PatchContractApplyResponse(
        applied=resolution.applied,
        rolled_back=resolution.rolled_back,
        applied_operations=resolution.applied_operations,
        fallback_mode=request.contract.fallback_mode,
        files=resolution.files,
        conflicts=[
            {
                "operation_index": conflict.operation_index,
                "path": conflict.path,
                "op": conflict.op,
                "code": conflict.code,
                "message": conflict.message,
                "fallback_applied": conflict.fallback_applied,
            }
            for conflict in resolution.conflicts
        ],
        project_id=project_id,
        generation_id=request.contract.generation_id,
        version=request.contract.version,
    )


@router.get("/{project_id}/preview-events")
async def stream_preview_events(
    project_id: UUID,
    request: Request,
    generation_id: Optional[UUID] = Query(default=None),
    entrypoint: str = Query(default="index.html", min_length=1, max_length=260),
    preview_token: Optional[str] = Query(default=None, min_length=16),
    poll_interval_ms: int = Query(default=1500, ge=250, le=15000),
    user: Optional[User] = Depends(get_current_user_optional),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Event stream for preview artifact updates."""
    resolved_generation_id = generation_id
    resolved_entrypoint = entrypoint.strip() or "index.html"

    if user is not None:
        project = await _get_project_for_user(project_id=project_id, user_id=user.id, db=db)
    else:
        token_value = preview_token or (credentials.credentials if credentials else None)
        if not token_value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = _decode_preview_session_claims(token_value)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid preview session token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        resolved_generation_id, resolved_entrypoint, _ = _resolve_preview_session_access(
            payload=payload,
            project_id=project_id,
            generation_id=generation_id,
            entrypoint=resolved_entrypoint,
        )
        project = await _get_project(project_id=project_id, db=db)

    poll_interval_seconds = poll_interval_ms / 1000

    async def _event_stream():
        yield "retry: 2000\n\n"
        last_emitted_generation_id: Optional[UUID] = None
        last_emitted_generation_version: int = -1

        while True:
            if await request.is_disconnected():
                break

            generation = await _get_preview_generation(
                project_id=project.id,
                db=db,
                generation_id=resolved_generation_id,
            )
            normalized_files = _normalize_preview_artifact_files(generation.files)
            preview_html = _select_preview_html(
                files=normalized_files,
                entrypoint=resolved_entrypoint,
                code_output=generation.code_output,
            )

            should_emit_update = (
                generation.id != last_emitted_generation_id
                or generation.version != last_emitted_generation_version
            )

            if should_emit_update:
                yield _serialize_sse_event(
                    "preview.updated",
                    {
                        "project_id": str(project.id),
                        "generation_id": str(generation.id),
                        "generation_version": max(generation.version, 1),
                        "entrypoint": resolved_entrypoint,
                        "preview_html": preview_html,
                        "files": [file.model_dump() for file in normalized_files],
                        "artifact_endpoint": _build_preview_artifact_endpoint(
                            project_id=project.id,
                            generation_id=generation.id,
                            entrypoint=resolved_entrypoint,
                        ),
                    },
                )
                last_emitted_generation_id = generation.id
                last_emitted_generation_version = generation.version

            yield _serialize_sse_event(
                "heartbeat",
                {
                    "project_id": str(project.id),
                    "generation_id": str(generation.id),
                    "generation_version": max(generation.version, 1),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await asyncio.sleep(poll_interval_seconds)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
