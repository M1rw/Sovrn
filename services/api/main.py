# =============================================================================
# SOVRN API - Main Application Entry Point
# =============================================================================
"""
SOVRN API Server
100% offline AI website builder backend
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sqlalchemy import text
import structlog

from app.core.config import settings
from app.core.errors import classify_exception
from app.core.database import engine, async_session
from app.api.v1.router import api_router
from app.lib.observability.http_metrics import http_request_metrics
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting SOVRN API", version=settings.VERSION, env=settings.ENVIRONMENT)
    
    # Verify database connection
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        raise
    
    # Verify inference service
    if settings.INFERENCE_URL:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.INFERENCE_URL}/health", timeout=10)
                if response.status_code == 200:
                    logger.info("Inference service connected", url=settings.INFERENCE_URL)
                else:
                    logger.warning("Inference service unhealthy", status=response.status_code)
        except Exception as e:
            logger.warning("Inference service unavailable", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down SOVRN API")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="SOVRN API",
    description="100% offline AI website builder API",
    version=settings.VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "service": "sovrn-api"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check for dependency health and deployment rollouts."""
    checks = {
        "database": False,
        "inference": False,
    }

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:
        logger.warning("Readiness check database failed", error=str(exc))

    if settings.INFERENCE_URL:
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.INFERENCE_URL}/health", timeout=5)
                checks["inference"] = response.status_code == 200
        except Exception as exc:
            logger.warning("Readiness check inference failed", error=str(exc))

    if all(checks.values()):
        return {
            "status": "ready",
            "version": settings.VERSION,
            "checks": checks,
        }

    return ORJSONResponse(
        status_code=503,
        content={
            "status": "degraded",
            "version": settings.VERSION,
            "checks": checks,
        },
    )


@app.get("/metrics/http")
async def http_metrics():
    """HTTP request latency and status metrics for observability dashboards."""
    if not settings.OBSERVABILITY_HTTP_METRICS_ENABLED:
        return {
            "enabled": False,
            "detail": "HTTP metrics are disabled.",
        }
    return http_request_metrics.snapshot()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "SOVRN API",
        "version": settings.VERSION,
        "docs": "/api/docs" if settings.DEBUG else None,
        "health": "/health"
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    classification = classify_exception(exc)
    request_id = getattr(request.state, "request_id", None)
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        correlation_id=correlation_id,
        retryable=classification.retryable,
        error_type=classification.error_type,
        error_code=classification.error_code,
        error=str(exc),
        exc_info=exc
    )
    return ORJSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": classification.error_code,
            "retryable": classification.retryable,
            "request_id": request_id,
            "correlation_id": correlation_id,
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
