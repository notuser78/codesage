"""
Rate limiting middleware
"""

import time
from typing import Dict, Optional, Tuple

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.database import redis_pool

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/health",
        "/ready",
        "/live",
        "/metrics",
    }
    
    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, list] = {}  # Fallback if Redis unavailable
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip rate limiting for exempt paths
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        allowed, retry_after = await self._check_rate_limit(client_id)
        
        if not allowed:
            return Response(
                content=f'{{"detail": "Rate limit exceeded. Retry after {retry_after} seconds."}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(retry_after)},
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining, reset_time = await self._get_rate_limit_info(client_id)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for the client"""
        # Try to get user ID from authenticated request
        user = getattr(request.state, "user", None)
        if user:
            return f"user:{user['id']}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    async def _check_rate_limit(self, client_id: str) -> Tuple[bool, int]:
        """Check if request is within rate limit"""
        key = f"rate_limit:{client_id}"
        window = settings.RATE_LIMIT_WINDOW
        max_requests = settings.RATE_LIMIT_REQUESTS
        
        try:
            if redis_pool:
                # Use Redis for distributed rate limiting
                pipe = redis_pool.pipeline()
                now = time.time()
                
                # Remove old entries
                pipe.zremrangebyscore(key, 0, now - window)
                
                # Count current requests
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(now): now})
                
                # Set expiry on the key
                pipe.expire(key, window)
                
                results = await pipe.execute()
                current_count = results[1]
                
                if current_count >= max_requests:
                    # Get oldest request time for retry-after
                    oldest = await redis_pool.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        retry_after = int(oldest[0][1] + window - now)
                    else:
                        retry_after = window
                    return False, max(0, retry_after)
                
                return True, 0
            else:
                # Use in-memory fallback
                return self._check_rate_limit_memory(client_id)
                
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request on error (fail open)
            return True, 0
    
    def _check_rate_limit_memory(self, client_id: str) -> Tuple[bool, int]:
        """In-memory rate limiting fallback"""
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW
        max_requests = settings.RATE_LIMIT_REQUESTS
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < window
        ]
        
        if len(self.requests[client_id]) >= max_requests:
            oldest = self.requests[client_id][0]
            retry_after = int(oldest + window - now)
            return False, max(0, retry_after)
        
        self.requests[client_id].append(now)
        return True, 0
    
    async def _get_rate_limit_info(self, client_id: str) -> Tuple[int, int]:
        """Get remaining requests and reset time"""
        key = f"rate_limit:{client_id}"
        window = settings.RATE_LIMIT_WINDOW
        max_requests = settings.RATE_LIMIT_REQUESTS
        
        try:
            if redis_pool:
                count = await redis_pool.zcard(key)
                remaining = max(0, max_requests - count)
                
                # Get reset time (oldest request + window)
                oldest = await redis_pool.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = int(oldest[0][1] + window)
                else:
                    reset_time = int(time.time() + window)
                
                return remaining, reset_time
            else:
                count = len(self.requests.get(client_id, []))
                return max(0, max_requests - count), int(time.time() + window)
                
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return 0, int(time.time() + window)


class RateLimiter:
    """Standalone rate limiter for specific endpoints"""
    
    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
        key_func=None,
    ):
        self.requests = requests
        self.window = window
        self.key_func = key_func or (lambda r: r.client.host)
    
    async def is_allowed(self, request: Request) -> Tuple[bool, dict]:
        """Check if request is allowed"""
        key = f"rate_limit:{self.key_func(request)}"
        
        try:
            if redis_pool:
                pipe = redis_pool.pipeline()
                now = time.time()
                
                pipe.zremrangebyscore(key, 0, now - self.window)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, self.window)
                
                results = await pipe.execute()
                current_count = results[1]
                
                remaining = max(0, self.requests - current_count)
                
                return current_count < self.requests, {
                    "limit": self.requests,
                    "remaining": remaining,
                    "window": self.window,
                }
            else:
                return True, {"limit": self.requests, "remaining": self.requests, "window": self.window}
                
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, {}
