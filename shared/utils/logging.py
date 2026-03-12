"""
Logging utilities
"""

import logging
import sys
from typing import Any, Dict

import structlog


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    service_name: str = "codesage",
):
    """Setup structured logging"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Add service name to all logs
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str = None):
    """Get a structured logger"""
    return structlog.get_logger(name)


class RequestContext:
    """Context for request-scoped logging"""
    
    def __init__(self, request_id: str = None, user_id: str = None):
        self.request_id = request_id
        self.user_id = user_id
    
    def bind(self):
        """Bind context to logger"""
        structlog.contextvars.bind_contextvars(
            request_id=self.request_id,
            user_id=self.user_id,
        )
    
    def clear(self):
        """Clear context"""
        structlog.contextvars.clear_contextvars()


def log_request(
    logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    **extra,
):
    """Log an HTTP request"""
    logger.info(
        "Request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **extra,
    )


def log_error(
    logger,
    error: Exception,
    context: Dict[str, Any] = None,
):
    """Log an error with context"""
    logger.error(
        str(error),
        error_type=type(error).__name__,
        context=context or {},
        exc_info=True,
    )
