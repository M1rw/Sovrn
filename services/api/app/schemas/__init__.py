# =============================================================================
# SOVRN API - Pydantic Schemas
# =============================================================================
"""
Request/Response schemas for API endpoints.
"""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# =============================================================================
# Base Schemas
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# Auth Schemas
# =============================================================================

class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = Field(None, max_length=255)
    locale: str = Field(default="en", max_length=10)


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseSchema):
    """Base user schema."""
    email: EmailStr
    name: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update schema."""
    name: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase, TimestampMixin):
    """User response schema."""
    id: UUID
    email_verified: bool
    is_active: bool
    is_admin: bool
    last_login_at: Optional[datetime] = None


class UserWithAccount(UserResponse):
    """User with account details."""
    account: Optional["AccountResponse"] = None


# =============================================================================
# Plan Schemas
# =============================================================================

class PlanResponse(BaseSchema):
    """Plan response schema."""
    id: UUID
    name: str
    type: str
    sparks_included: int
    price_cents: int
    features: dict


# =============================================================================
# Account Schemas
# =============================================================================

class AccountResponse(BaseSchema):
    """Account response schema."""
    id: UUID
    sparks_balance: int
    sparks_used_total: int
    plan: PlanResponse
    plan_started_at: datetime
    plan_expires_at: Optional[datetime] = None


class SparkLedgerEntry(BaseSchema):
    """Spark ledger entry schema."""
    id: UUID
    type: str
    amount: int
    balance_after: int
    description: Optional[str] = None
    reference_type: Optional[str] = None
    created_at: datetime


class TopUpRequest(BaseModel):
    """Admin spark top-up request."""
    amount: int = Field(..., gt=0, le=10000)
    description: Optional[str] = None


# =============================================================================
# Invoice Schemas
# =============================================================================

class InvoiceResponse(BaseSchema):
    """Invoice response schema."""
    id: UUID
    invoice_number: str
    amount_cents: int
    currency: str
    status: str
    sparks_amount: int
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime


class CreateInvoiceRequest(BaseModel):
    """Create invoice request."""
    plan_type: str
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class ApproveInvoiceRequest(BaseModel):
    """Approve invoice request (admin)."""
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# Project Schemas
# =============================================================================

class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    locale: str = Field(default="en", max_length=10)
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_audience: Optional[dict] = None
    goals: Optional[list] = None
    brief: Optional[str] = None
    settings: Optional[dict] = None


class ProjectCreate(ProjectBase):
    """Project creation schema."""
    pass


class ProjectUpdate(BaseModel):
    """Project update schema."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    locale: Optional[str] = Field(None, max_length=10)
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_audience: Optional[dict] = None
    goals: Optional[list] = None
    brief: Optional[str] = None
    settings: Optional[dict] = None


class ProjectResponse(ProjectBase, TimestampMixin, BaseSchema):
    """Project response schema."""
    id: UUID
    user_id: UUID
    slug: Optional[str] = None
    status: str
    generated_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    deploy_url: Optional[str] = None


class ProjectWithGenerations(ProjectResponse):
    """Project with generation history."""
    generations: list["SiteGenerationResponse"] = []


# =============================================================================
# Job Schemas
# =============================================================================

class JobCreate(BaseModel):
    """Job creation schema."""
    type: str = Field(..., pattern="^(strategy|design|engineer|full)$")
    input: Optional[dict] = None
    priority: int = Field(default=0, ge=0, le=10)


class JobResponse(BaseSchema):
    """Job response schema."""
    id: UUID
    project_id: UUID
    type: str
    status: str
    spark_cost: int
    priority: int
    input: dict
    output: dict
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class JobStatusUpdate(BaseModel):
    """Job status update (internal)."""
    status: str
    output: Optional[dict] = None
    error: Optional[str] = None


# =============================================================================
# Site Generation Schemas
# =============================================================================

class SiteGenerationResponse(BaseSchema):
    """Site generation response schema."""
    id: UUID
    project_id: UUID
    job_id: Optional[UUID] = None
    version: int
    strategy_output: dict
    design_output: dict
    code_output: dict
    files: list
    lighthouse_scores: dict
    created_at: datetime


class PreviewArtifactFile(BaseModel):
    """A normalized file payload used for browser preview runtime mounting."""

    path: str
    content: str
    language: Optional[str] = None
    size_bytes: int = Field(default=0, ge=0)


class PreviewArtifactResponse(BaseModel):
    """Project artifact payload for preview runtime bootstrap."""

    project_id: UUID
    generation_id: UUID
    generation_version: int = Field(ge=1)
    entrypoint: str = "index.html"
    preview_html: str
    files: list[PreviewArtifactFile]
    source: str = "site_generation"


class PreviewSessionRequest(BaseModel):
    """Request payload for issuing a signed preview session token."""

    generation_id: Optional[UUID] = None
    entrypoint: str = Field(default="index.html", min_length=1, max_length=260)
    ttl_seconds: Optional[int] = Field(default=None, ge=60, le=86400)


class PreviewSessionResponse(BaseModel):
    """Signed token response for preview runtime bootstrap."""

    token: str
    token_type: str = "preview_session"
    expires_at: datetime
    project_id: UUID
    generation_id: UUID
    entrypoint: str
    artifact_endpoint: str


class PreviewSessionVerifyRequest(BaseModel):
    """Request payload for preview-session token verification."""

    token: str = Field(..., min_length=16)
    generation_id: Optional[UUID] = None
    entrypoint: Optional[str] = Field(default=None, min_length=1, max_length=260)


class PreviewSessionVerifyResponse(BaseModel):
    """Result payload for preview-session token verification."""

    valid: bool = True
    token_type: str = "preview_session"
    project_id: UUID
    generation_id: UUID
    entrypoint: str
    expires_at: datetime
    artifact_endpoint: str


# =============================================================================
# Phase 3 Patch Contract Schemas
# =============================================================================

PatchLanguage = Literal["ts", "tsx", "js", "jsx", "json", "css", "html"]
PatchOperationType = Literal["replace_file", "replace_range"]


class PatchTextRange(BaseModel):
    """Character-offset range for deterministic partial edits."""

    model_config = ConfigDict(extra="forbid")

    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "PatchTextRange":
        if self.end < self.start:
            raise ValueError("Patch range end must be greater than or equal to start")
        return self


class PatchOperation(BaseModel):
    """Single deterministic patch operation over a project file."""

    model_config = ConfigDict(extra="forbid")

    op: PatchOperationType
    path: str = Field(..., min_length=1, max_length=260)
    language: Optional[PatchLanguage] = None
    expected_sha256: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    range: Optional[PatchTextRange] = None
    content: str = Field(default="", max_length=1_000_000)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip()

        if not normalized:
            raise ValueError("Patch path must not be empty")
        if normalized.startswith("/"):
            raise ValueError("Patch path must be relative")
        if normalized in {".", ".."}:
            raise ValueError("Patch path must target a file")
        if normalized.startswith("../") or "/../" in normalized:
            raise ValueError("Patch path traversal is not allowed")
        if "\x00" in normalized:
            raise ValueError("Patch path must not include null bytes")

        return normalized

    @model_validator(mode="after")
    def validate_shape(self) -> "PatchOperation":
        if self.op == "replace_file" and self.range is not None:
            raise ValueError("replace_file must not include range")

        if self.op == "replace_range" and self.range is None:
            raise ValueError("replace_range requires range")

        return self


class PatchContractRequest(BaseModel):
    """Phase 3 patch contract payload for deterministic file updates."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    project_id: Optional[UUID] = None
    generation_id: Optional[UUID] = None
    fallback_mode: Literal["safe_rewrite", "reject"] = "safe_rewrite"
    operations: list[PatchOperation] = Field(..., min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_unique_targets(self) -> "PatchContractRequest":
        seen: set[tuple[str, int, int]] = set()
        for operation in self.operations:
            if operation.range is None:
                key = (operation.path, -1, -1)
            else:
                key = (operation.path, operation.range.start, operation.range.end)

            if key in seen:
                raise ValueError(
                    "Duplicate patch operation target detected; path+range must be unique"
                )
            seen.add(key)

        return self


class PatchContractValidationResponse(BaseModel):
    """Validation receipt for a patch contract payload."""

    valid: bool = True
    project_id: UUID
    generation_id: Optional[UUID] = None
    version: str
    operation_count: int = Field(..., ge=1)
    files_touched: list[str]
    fallback_mode: Literal["safe_rewrite", "reject"]


class PatchConflictItem(BaseModel):
    """Single patch conflict raised during patch-contract resolution."""

    operation_index: int = Field(..., ge=0)
    path: str
    op: PatchOperationType
    code: Literal["missing_file", "hash_mismatch", "invalid_range"]
    message: str
    fallback_applied: bool = False


class PatchContractApplyRequest(BaseModel):
    """Request payload for applying a patch contract against in-memory files."""

    contract: PatchContractRequest
    files: dict[str, str] = Field(default_factory=dict)


class PatchContractApplyResponse(BaseModel):
    """Result payload for patch-contract conflict resolution and rollback handling."""

    applied: bool
    rolled_back: bool
    applied_operations: int = Field(..., ge=0)
    fallback_mode: Literal["safe_rewrite", "reject"]
    files: dict[str, str]
    conflicts: list[PatchConflictItem] = Field(default_factory=list)
    project_id: UUID
    generation_id: Optional[UUID] = None
    version: str


# =============================================================================
# Generation Request Schemas
# =============================================================================

class GenerateSiteRequest(BaseModel):
    """Full site generation request."""
    brief: str = Field(..., min_length=10, max_length=10000)
    locale: str = Field(default="en", max_length=10)
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_audience: Optional[dict] = None
    goals: Optional[list] = None
    template_id: Optional[UUID] = None
    settings: Optional[dict] = None


class GenerationProgress(BaseModel):
    """Generation progress update."""
    job_id: UUID
    status: str
    progress: int = Field(..., ge=0, le=100)
    stage: str
    message: Optional[str] = None


# =============================================================================
# Locale Rules Schemas
# =============================================================================

class LocaleRuleResponse(BaseSchema):
    """Locale rule response schema."""
    id: UUID
    locale: str
    country_code: Optional[str] = None
    region: Optional[str] = None
    rules: dict
    payment_methods: list
    legal_requirements: list
    trust_signals: list
    ui_patterns: dict
    is_active: bool


# =============================================================================
# Template Schemas
# =============================================================================

class TemplateResponse(BaseSchema):
    """Template response schema."""
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    category: Optional[str] = None
    industry: Optional[str] = None
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_premium: bool
    usage_count: int


# =============================================================================
# Common Responses
# =============================================================================

class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str
    type: str = "error"
    errors: Optional[list[dict]] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


# Update forward references
UserWithAccount.model_rebuild()
ProjectWithGenerations.model_rebuild()
