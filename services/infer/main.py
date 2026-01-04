# =============================================================================
# SOVRN Inference Service - Main Application
# =============================================================================
"""
FastAPI server for llama.cpp inference with OpenAI-compatible API
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

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


@app.get("/stats")
async def get_stats():
    """Get inference statistics."""
    return inference_engine.get_stats()


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
