from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for worker-side lightweight models."""


class Job(Base):
    """Minimal Job model shared by worker polling and processor logic."""

    __tablename__ = "jobs"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    project_id = Column(PGUUID(as_uuid=True), nullable=False)
    type = Column(SQLEnum("strategy", "design", "engineer", "full", name="job_type"), nullable=False)
    status = Column(
        SQLEnum("queued", "processing", "completed", "failed", "cancelled", name="job_status"),
        nullable=False,
    )
    spark_cost = Column(Integer, default=1)
    priority = Column(Integer, default=0)
    input = Column(JSONB, default=dict)
    output = Column(JSONB, default=dict)
    error = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    worker_id = Column(String(100))
