"""
Structured logging middleware
"""

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware"""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Log request
        await self._log_request(request)

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        await self._log_response(request, response, duration_ms)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    async def _log_request(self, request: Request):
        """Log incoming request"""
        client_host = request.client.host if request.client else "unknown"

        logger.info(
            "Request started",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client_ip=client_host,
            user_agent=request.headers.get("user-agent"),
        )

    async def _log_response(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
    ):
        """Log outgoing response"""
        logger.info(
            "Request completed",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            content_length=response.headers.get("content-length"),
        )


class RequestContext:
    """Helper class for request context logging"""

    @staticmethod
    def get_request_id(request: Request) -> str:
        """Get request ID from request state"""
        return getattr(request.state, "request_id", "unknown")

    @staticmethod
    def get_user_id(request: Request) -> str:
        """Get user ID from request state"""
        user = getattr(request.state, "user", None)
        return user.get("id") if user else "anonymous"

    @staticmethod
    def bind_logger(request: Request):
        """Bind request context to logger"""
        return logger.bind(
            request_id=RequestContext.get_request_id(request),
            user_id=RequestContext.get_user_id(request),
        )


def setup_logging():
    """Configure structured logging"""
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
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
