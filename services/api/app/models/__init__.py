# =============================================================================
# SOVRN API - Database Models
# =============================================================================
"""
SQLAlchemy ORM models for all database tables.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text,
    Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, INET, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


# =============================================================================
# Enums
# =============================================================================

class PlanType(str, Enum):
    FREE = "free"
    FREELANCER = "freelancer"
    BUSINESS = "business"
    AGENCY = "agency"
    
    def __str__(self):
        return self.value


class LedgerType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"
    BONUS = "bonus"
    EXPIRED = "expired"


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    STRATEGY = "strategy"
    DESIGN = "design"
    ENGINEER = "engineer"
    FULL = "full"


# =============================================================================
# User Model
# =============================================================================

class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    locale: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="user", uselist=False)
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="user")


# =============================================================================
# Plans & Accounts
# =============================================================================

class Plan(Base):
    """Subscription plan model."""
    
    __tablename__ = "plans"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    type: Mapped[PlanType] = mapped_column(SQLEnum(PlanType, name='plan_type', values_callable=lambda x: [e.value for e in x]), unique=True, nullable=False)
    sparks_included: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="plan")


class Account(Base):
    """User account with sparks balance."""
    
    __tablename__ = "accounts"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("plans.id"))
    
    sparks_balance: Mapped[int] = mapped_column(Integer, default=0)
    sparks_used_total: Mapped[int] = mapped_column(Integer, default=0)
    
    plan_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="account")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="accounts")
    ledger_entries: Mapped[list["SparkLedger"]] = relationship("SparkLedger", back_populates="account")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="account")


class SparkLedger(Base):
    """Spark transaction ledger."""
    
    __tablename__ = "spark_ledger"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    type: Mapped[LedgerType] = mapped_column(SQLEnum(LedgerType, name='ledger_type', values_callable=lambda x: [e.value for e in x]), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    reference_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    reference_type: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="ledger_entries")


# =============================================================================
# Invoices
# =============================================================================

class Invoice(Base):
    """Payment invoice model."""
    
    __tablename__ = "invoices"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[InvoiceStatus] = mapped_column(SQLEnum(InvoiceStatus, name='invoice_status', values_callable=lambda x: [e.value for e in x]), default=InvoiceStatus.PENDING, index=True)
    
    plan_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("plans.id"))
    sparks_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))
    payment_reference: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="invoices")


# =============================================================================
# Projects
# =============================================================================

class Project(Base):
    """Website project model."""
    
    __tablename__ = "projects"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus, name='project_status', values_callable=lambda x: [e.value for e in x]), default=ProjectStatus.DRAFT, index=True)
    
    locale: Mapped[str] = mapped_column(String(10), default="en")
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    business_type: Mapped[Optional[str]] = mapped_column(String(100))
    target_audience: Mapped[dict] = mapped_column(JSONB, default=dict)
    goals: Mapped[list] = mapped_column(JSONB, default=list)
    brief: Mapped[Optional[str]] = mapped_column(Text)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deploy_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="project")
    generations: Mapped[list["SiteGeneration"]] = relationship("SiteGeneration", back_populates="project")


# =============================================================================
# Jobs
# =============================================================================

class Job(Base):
    """Generation job model."""
    
    __tablename__ = "jobs"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    
    type: Mapped[JobType] = mapped_column(SQLEnum(JobType, name='job_type', values_callable=lambda x: [e.value for e in x]), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus, name='job_status', values_callable=lambda x: [e.value for e in x]), default=JobStatus.QUEUED, index=True)
    spark_cost: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    worker_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")
    generation: Mapped[Optional["SiteGeneration"]] = relationship("SiteGeneration", back_populates="job", uselist=False)
    
    # Index for job queue
    __table_args__ = (
        Index("idx_jobs_queue", "status", "priority", "created_at", postgresql_where=(status == JobStatus.QUEUED)),
    )


# =============================================================================
# Site Generations
# =============================================================================

class SiteGeneration(Base):
    """Generated site output model."""
    
    __tablename__ = "site_generations"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("jobs.id"))
    
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    strategy_output: Mapped[dict] = mapped_column(JSONB, default=dict)
    design_output: Mapped[dict] = mapped_column(JSONB, default=dict)
    code_output: Mapped[dict] = mapped_column(JSONB, default=dict)
    files: Mapped[list] = mapped_column(JSONB, default=list)
    lighthouse_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="generations")
    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="generation")


# =============================================================================
# Locale Rules
# =============================================================================

class LocaleRule(Base):
    """Cultural adaptation rules by locale."""
    
    __tablename__ = "locale_rules"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    region: Mapped[Optional[str]] = mapped_column(String(50))
    
    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    payment_methods: Mapped[list] = mapped_column(JSONB, default=list)
    legal_requirements: Mapped[list] = mapped_column(JSONB, default=list)
    trust_signals: Mapped[list] = mapped_column(JSONB, default=list)
    ui_patterns: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint("locale", "country_code", name="uq_locale_country"),
    )


# =============================================================================
# Embeddings (for RAG)
# =============================================================================

class Embedding(Base):
    """Vector embeddings for RAG."""
    
    __tablename__ = "embeddings"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(384))
    embedding_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)  # Renamed to avoid conflict with SQLAlchemy
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# =============================================================================
# Templates
# =============================================================================

class Template(Base):
    """Site template model."""
    
    __tablename__ = "templates"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    preview_url: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =============================================================================
# Audit Log
# =============================================================================

class AuditLog(Base):
    """Audit log for tracking changes."""
    
    __tablename__ = "audit_log"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
