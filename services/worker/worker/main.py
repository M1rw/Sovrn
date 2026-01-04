# =============================================================================
# SOVRN Worker - Background Job Processor
# =============================================================================
"""
Worker service for processing generation jobs asynchronously.
Polls database for queued jobs and processes them.
"""

import asyncio
import signal
import sys
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import structlog

from worker.config import settings
from worker.processor import JobProcessor


# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


class Worker:
    """Background job worker."""
    
    def __init__(self):
        self.worker_id = f"worker-{uuid4().hex[:8]}"
        self.running = False
        self.current_job: Optional[UUID] = None
        
        # Database
        self.engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            echo=settings.DEBUG,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Job processor - pass both inference URL and API URL
        self.processor = JobProcessor(
            self.session_factory, 
            settings.INFERENCE_URL,
            api_url=settings.API_URL
        )
    
    async def start(self):
        """Start the worker."""
        logger.info("Worker starting", worker_id=self.worker_id)
        self.running = True
        
        # Register signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        
        # Main loop
        while self.running:
            try:
                job = await self._claim_job()
                
                if job:
                    self.current_job = job["id"]
                    await self.processor.process(job)
                    self.current_job = None
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(settings.POLL_INTERVAL)
                    
            except Exception as e:
                logger.error("Worker error", error=str(e))
                await asyncio.sleep(5)  # Back off on error
        
        logger.info("Worker stopped", worker_id=self.worker_id)
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Worker shutting down", worker_id=self.worker_id)
        self.running = False
        
        # If processing a job, mark it back as queued
        if self.current_job:
            async with self.session_factory() as session:
                await session.execute(
                    update(Job)
                    .where(Job.id == self.current_job)
                    .values(status="queued", worker_id=None)
                )
                await session.commit()
        
        await self.engine.dispose()
    
    async def _claim_job(self) -> Optional[dict]:
        """Try to claim a queued job."""
        async with self.session_factory() as session:
            # Find and claim a job atomically
            result = await session.execute(
                select(Job)
                .where(Job.status == "queued")
                .order_by(Job.priority.desc(), Job.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return None
            
            # Claim the job
            job.status = "processing"
            job.worker_id = self.worker_id
            job.started_at = datetime.now(timezone.utc)
            
            await session.commit()
            
            return {
                "id": job.id,
                "project_id": job.project_id,
                "type": job.type,
                "input": job.input,
                "spark_cost": job.spark_cost,
            }


# Import Job model for the query
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Job(Base):
    """Minimal Job model for worker."""
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


def main():
    """Main entry point."""
    worker = Worker()
    asyncio.run(worker.start())


if __name__ == "__main__":
    main()
