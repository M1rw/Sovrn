# =============================================================================
# SOVRN Worker - Job Processor
# =============================================================================
"""
Processes generation jobs by calling agents.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import structlog

from worker.config import settings


logger = structlog.get_logger()


class JobProcessor:
    """Processes generation jobs."""
    
    def __init__(self, session_factory: async_sessionmaker, inference_url: str, api_url: str = "http://api:8000"):
        self.session_factory = session_factory
        self.inference_url = inference_url
        self.api_url = api_url
    
    async def process(self, job: dict) -> None:
        """Process a single job."""
        job_id = job["id"]
        logger.info("Processing job", job_id=str(job_id), type=job["type"])
        
        try:
            # Call API to run generation pipeline with real AI agents
            async with httpx.AsyncClient(timeout=settings.JOB_TIMEOUT) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/internal/process-job",
                    json={"job_id": str(job_id)}
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error("API call failed", status=response.status_code, error=error_text)
                    raise Exception(f"Generation failed: {error_text}")
                
                result = response.json()
            
            # Extract the output
            output = result.get("output", {})
            
            # Mark job as completed
            await self._complete_job(job_id, output)
            logger.info("Job completed", job_id=str(job_id))
            
        except Exception as e:
            logger.error("Job failed", job_id=str(job_id), error=str(e))
            await self._fail_job(job_id, str(e))
    
    async def _complete_job(self, job_id: UUID, output: dict) -> None:
        """Mark job as completed."""
        async with self.session_factory() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(
                    status="completed",
                    output=output,
                    completed_at=datetime.now(timezone.utc)
                )
            )
            await session.commit()
    
    async def _fail_job(self, job_id: UUID, error: str) -> None:
        """Mark job as failed."""
        async with self.session_factory() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(
                    status="failed",
                    error=error,
                    completed_at=datetime.now(timezone.utc)
                )
            )
            await session.commit()


# Import Job model
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    project_id = Column(PGUUID(as_uuid=True), nullable=False)
    type = Column(SQLEnum('strategy', 'design', 'engineer', 'full', name='job_type'), nullable=False)
    status = Column(SQLEnum('queued', 'processing', 'completed', 'failed', 'cancelled', name='job_status'), nullable=False)
    spark_cost = Column(Integer, default=1)
    priority = Column(Integer, default=0)
    input = Column(JSONB, default={})
    output = Column(JSONB, default={})
    error = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    worker_id = Column(String(100))
