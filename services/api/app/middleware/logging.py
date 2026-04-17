# =============================================================================
# SOVRN API - Middleware: Logging
# =============================================================================
"""
Request/Response logging middleware.
"""

import time
from secrets import token_hex
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.config import settings
from app.lib.observability.http_metrics import http_request_metrics

logger = structlog.get_logger()


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
    if trace_id == "0" * 32:
        return None
    if parent_span_id == "0" * 16:
        return None
    if not _is_valid_hex(trace_id, 32):
        return None
    if not _is_valid_hex(parent_span_id, 16):
        return None

    return trace_id, parent_span_id


def _resolve_route_path(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return request.url.path


def _build_trace_context(incoming_traceparent: str | None) -> tuple[str, str, str | None, str]:
    parsed = (
        _parse_traceparent(incoming_traceparent)
        if settings.OBSERVABILITY_TRACE_PROPAGATION_ENABLED
        else None
    )
    trace_id = parsed[0] if parsed else token_hex(16)
    parent_span_id = parsed[1] if parsed else None
    span_id = token_hex(8)
    traceparent = f"00-{trace_id}-{span_id}-01"
    return trace_id, span_id, parent_span_id, traceparent


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Request ID is always generated server-side for uniqueness.
        request_id = str(uuid4())
        # Correlation ID can be propagated from upstream clients/services.
        correlation_id = request.headers.get("X-Correlation-ID", request_id)
        client_session_id = request.headers.get("X-Client-Session-ID")
        trace_id, span_id, parent_span_id, traceparent = _build_trace_context(
            request.headers.get("traceparent")
        )

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.client_session_id = client_session_id
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        request.state.parent_span_id = parent_span_id
        request.state.traceparent = traceparent
        
        # Bind request ID to logger context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
            client_session_id=client_session_id,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
        )
        
        # Start timer
        start_time = time.perf_counter()
        if settings.OBSERVABILITY_HTTP_METRICS_ENABLED:
            http_request_metrics.start_request()

        status_code = 500
        error_type: str | None = None
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            traceparent=traceparent,
        )
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            # Add request ID header
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Trace-ID"] = trace_id
            response.headers["traceparent"] = traceparent
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_type = e.__class__.__name__
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(e),
                error_type=error_type,
            )
            raise
        finally:
            if settings.OBSERVABILITY_HTTP_METRICS_ENABLED:
                duration_ms = (time.perf_counter() - start_time) * 1000
                http_request_metrics.finish_request(
                    method=request.method,
                    route_path=_resolve_route_path(request),
                    status_code=status_code,
                    duration_ms=duration_ms,
                    error_type=error_type,
                )
            structlog.contextvars.clear_contextvars()
