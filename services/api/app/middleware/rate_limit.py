# =============================================================================
# SOVRN API - Middleware: Rate Limiting
# =============================================================================
"""
Simple in-memory rate limiting middleware.
For production, consider Redis-based rate limiting.
"""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware using sliding window."""
    
    def __init__(self, app):
        super().__init__(app)
        # Store: {client_key: [(timestamp, count), ...]}
        self.requests: Dict[str, list[Tuple[float, int]]] = defaultdict(list)
        self.window_size = 60  # 1 minute window
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use IP address as default key
        client_ip = request.client.host if request.client else "unknown"
        
        # If authenticated, use user ID instead
        # This would be set by auth middleware
        user_id = getattr(request.state, "user_id", None)
        
        return f"user:{user_id}" if user_id else f"ip:{client_ip}"
    
    def _cleanup_old_requests(self, key: str, now: float) -> None:
        """Remove requests outside the window."""
        cutoff = now - self.window_size
        self.requests[key] = [
            (ts, count) for ts, count in self.requests[key]
            if ts > cutoff
        ]
    
    def _count_requests(self, key: str) -> int:
        """Count requests in current window."""
        return sum(count for _, count in self.requests[key])
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip health checks
        if request.url.path in [
            "/health",
            "/ready",
            "/",
            "/metrics/http",
            "/api/docs",
            "/api/openapi.json",
        ]:
            return await call_next(request)
        
        client_key = self._get_client_key(request)
        now = time.time()
        
        # Cleanup old entries
        self._cleanup_old_requests(client_key, now)
        
        # Check rate limit
        current_count = self._count_requests(client_key)
        limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        
        if current_count >= limit:
            # Calculate retry-after
            oldest_request = min(ts for ts, _ in self.requests[client_key]) if self.requests[client_key] else now
            retry_after = int(self.window_size - (now - oldest_request)) + 1
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(oldest_request + self.window_size))
                }
            )
        
        # Record this request
        self.requests[client_key].append((now, 1))
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, limit - current_count - 1)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
