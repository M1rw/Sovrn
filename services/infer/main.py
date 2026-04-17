# =============================================================================
# SOVRN Inference Service - Main Application
# =============================================================================
"""
FastAPI server for llama.cpp inference with OpenAI-compatible API
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from secrets import token_hex
import subprocess
import sys
import time
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

from config import settings
from model_manager import model_manager
from inference_engine import (
    inference_engine,
    ChatCompletionRequest,
    CompletionRequest,
    ChatCompletionResponse,
    CompletionResponse
)

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
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

requests_total = None
request_duration = None
tokens_generated_total = None
active_requests = None


def _is_valid_hex(value: str, expected_length: int) -> bool:
    if len(value) != expected_length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _parse_traceparent(header_value: str | None) -> tuple[str, str] | None:
    if not header_value:
        return None

    parts = header_value.strip().split("-")
    if len(parts) != 4:
        return None

    _, trace_id, parent_span_id, _ = parts
    if trace_id == "0" * 32 or parent_span_id == "0" * 16:
        return None
    if not _is_valid_hex(trace_id, 32) or not _is_valid_hex(parent_span_id, 16):
        return None
    return trace_id, parent_span_id


def _build_trace_context(incoming_traceparent: str | None) -> tuple[str, str, str | None, str]:
    parsed = _parse_traceparent(incoming_traceparent)
    trace_id = parsed[0] if parsed else token_hex(16)
    parent_span_id = parsed[1] if parsed else None
    span_id = token_hex(8)
    traceparent = f"00-{trace_id}-{span_id}-01"
    return trace_id, span_id, parent_span_id, traceparent


def _process_metrics() -> dict:
    rss_mb = None
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_value = usage.ru_maxrss
        if sys.platform == "darwin":
            rss_mb = round(rss_value / (1024 * 1024), 2)
        else:
            rss_mb = round(rss_value / 1024, 2)
    except Exception:
        rss_mb = None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rss_mb": rss_mb,
    }


def _gpu_metrics() -> dict:
    """Best-effort GPU telemetry using nvidia-smi when available."""
    command = [
        "nvidia-smi",
        "--query-gpu=utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=2)
    except Exception:
        return {
            "available": False,
            "detail": "nvidia-smi not available",
        }

    if completed.returncode != 0 or not completed.stdout.strip():
        return {
            "available": False,
            "detail": "gpu telemetry unavailable",
        }

    first_line = completed.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in first_line.split(",")]
    if len(parts) < 3:
        return {
            "available": False,
            "detail": "unexpected nvidia-smi output",
        }

    try:
        utilization_pct = float(parts[0])
        memory_used_mb = float(parts[1])
        memory_total_mb = float(parts[2])
    except ValueError:
        return {
            "available": False,
            "detail": "failed to parse gpu metrics",
        }

    memory_utilization = 0.0
    if memory_total_mb > 0:
        memory_utilization = memory_used_mb / memory_total_mb

    return {
        "available": True,
        "gpu_utilization_pct": round(utilization_pct, 2),
        "memory_used_mb": round(memory_used_mb, 2),
        "memory_total_mb": round(memory_total_mb, 2),
        "memory_utilization": round(memory_utilization, 4),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(
        "starting_inference_service",
        model_path=str(settings.MODEL_PATH),
        n_gpu_layers=settings.N_GPU_LAYERS,
        max_concurrent=settings.MAX_CONCURRENT_REQUESTS
    )
    
    # Load model on startup (optional - continue even if model not found)
    try:
        await model_manager.load_model()
        logger.info("model_loaded_successfully")
    except Exception as e:
        logger.warning("model_load_failed_starting_without_model", error=str(e))
        # Continue without model - users can load one later via API
    
    yield
    
    # Shutdown
    logger.info("shutting_down_inference_service")
    await model_manager.unload_model()


# Create FastAPI app
app = FastAPI(
    title="SOVRN Inference API",
    description="OpenAI-compatible inference API powered by llama.cpp",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = f"inf-{uuid4().hex[:16]}"
    correlation_id = request.headers.get("X-Correlation-ID", request_id)
    client_session_id = request.headers.get("X-Client-Session-ID")
    trace_id, span_id, parent_span_id, traceparent = _build_trace_context(
        request.headers.get("traceparent")
    )
    started_at = time.perf_counter()

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    request.state.trace_id = trace_id
    request.state.span_id = span_id

    if settings.ENABLE_METRICS and active_requests is not None:
        active_requests.inc()

    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.error(
            "inference_request_failed",
            path=request.url.path,
            method=request.method,
            request_id=request_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            duration_ms=round(duration_ms, 2),
            error=str(exc),
            error_type=exc.__class__.__name__,
        )
        raise
    finally:
        if settings.ENABLE_METRICS and active_requests is not None:
            active_requests.dec()

    duration_ms = (time.perf_counter() - started_at) * 1000
    if settings.ENABLE_METRICS:
        if requests_total is not None:
            requests_total.labels(endpoint=request.url.path, status=str(status_code)).inc()
        if request_duration is not None:
            request_duration.labels(endpoint=request.url.path).observe(duration_ms / 1000)

    logger.info(
        "inference_request_completed",
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        correlation_id=correlation_id,
        client_session_id=client_session_id,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Trace-ID"] = trace_id
    response.headers["traceparent"] = traceparent
    return response


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model_manager.is_loaded(),
        "model_info": model_manager.get_model_info()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness endpoint that verifies model availability for serving requests."""
    model_loaded = model_manager.is_loaded()
    if model_loaded:
        return {
            "status": "ready",
            "model_loaded": True,
            "model_info": model_manager.get_model_info(),
        }
    return ORJSONResponse(
        status_code=503,
        content={
            "status": "degraded",
            "model_loaded": False,
            "detail": "No model loaded",
        },
    )


@app.get("/stats")
async def get_stats():
    """Get inference statistics."""
    return inference_engine.get_stats()


@app.get("/metrics/system")
async def get_system_metrics():
    """Get process and runtime telemetry for saturation monitoring."""
    return {
        "service": "sovrn-infer",
        "runtime": _process_metrics(),
        "gpu": _gpu_metrics(),
        "inference": inference_engine.get_stats(),
    }


# =============================================================================
# OpenAI-Compatible Endpoints
# =============================================================================

@app.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest
) -> ChatCompletionResponse:
    """
    Create chat completion (OpenAI-compatible).
    
    Supports both streaming and non-streaming responses.
    """
    if not model_manager.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="No model loaded. Use /admin/load-model to load a model first."
        )
    
    try:
        if request.stream:
            # Return streaming response
            generator = await inference_engine.chat_completion(request)
            return StreamingResponse(
                generator,
                media_type="text/event-stream"
            )
        else:
            # Return complete response
            response = await inference_engine.chat_completion(request)
            return response
            
    except Exception as e:
        logger.error(
            "chat_completion_error",
            error=str(e),
            messages_count=len(request.messages)
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/completions")
async def create_completion(
    request: CompletionRequest
) -> CompletionResponse:
    """
    Create text completion (OpenAI-compatible).
    """
    if not model_manager.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="No model loaded. Use /admin/load-model to load a model first."
        )
    
    try:
        if request.stream:
            generator = await inference_engine.text_completion(request)
            return StreamingResponse(
                generator,
                media_type="text/event-stream"
            )
        else:
            response = await inference_engine.text_completion(request)
            return response
            
    except Exception as e:
        logger.error(
            "text_completion_error",
            error=str(e),
            prompt_length=len(request.prompt)
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models")
async def list_models():
    """List available models."""
    available_models = await model_manager.list_available_models()
    current_model = model_manager.get_model_info()
    
    models = []
    for name, path in available_models.items():
        models.append({
            "id": name,
            "object": "model",
            "created": int(path.stat().st_ctime),
            "owned_by": "sovrn",
            "active": current_model and current_model["name"] == name
        })
    
    return {
        "object": "list",
        "data": models
    }


# =============================================================================
# Admin Endpoints
# =============================================================================

@app.post("/admin/load-model")
async def load_model(model_name: str):
    """Load a specific model (admin only)."""
    try:
        models = await model_manager.list_available_models()
        
        if model_name not in models:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_name}' not found"
            )
        
        model_path = models[model_name]
        await model_manager.load_model(model_path)
        
        return {
            "success": True,
            "model": model_manager.get_model_info()
        }
        
    except Exception as e:
        logger.error("model_load_error", model_name=model_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/unload-model")
async def unload_model():
    """Unload current model (admin only)."""
    await model_manager.unload_model()
    return {"success": True, "message": "Model unloaded"}


# =============================================================================
# Prometheus Metrics (if enabled)
# =============================================================================

if settings.ENABLE_METRICS:
    from prometheus_client import Counter, Histogram, Gauge, make_asgi_app, CollectorRegistry, REGISTRY
    
    # Check if metrics already registered (for reloads)
    try:
        requests_total = Counter(
            'inference_requests_total',
            'Total inference requests',
            ['endpoint', 'status']
        )
    except ValueError:
        # Already registered, get from registry
        requests_total = REGISTRY._names_to_collectors['inference_requests_total']
    
    try:
        request_duration = Histogram(
            'inference_request_duration_seconds',
            'Request duration in seconds',
            ['endpoint']
        )
    except ValueError:
        request_duration = REGISTRY._names_to_collectors['inference_request_duration_seconds']
    
    try:
        tokens_generated_total = Counter(
            'inference_tokens_generated_total',
            'Total tokens generated'
        )
    except ValueError:
        tokens_generated_total = REGISTRY._names_to_collectors['inference_tokens_generated_total']
    
    try:
        active_requests = Gauge(
            'inference_active_requests',
            'Currently active inference requests'
        )
    except ValueError:
        active_requests = REGISTRY._names_to_collectors['inference_active_requests']
    
    # Mount metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False  # Don't reload (model is expensive to load)
    )
