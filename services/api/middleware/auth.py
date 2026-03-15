"""
Authentication middleware
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings

logger = structlog.get_logger()
security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware"""

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/health",
        "/ready",
        "/live",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }

    async def dispatch(self, request: Request, call_next):
        # Check if path is public
        path = request.url.path
        if any(path.startswith(public) for public in self.PUBLIC_PATHS):
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response(
                content='{"detail": "Authorization header missing"}',
                status_code=401,
                media_type="application/json",
            )

        # Validate token
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid scheme")

            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )

            # Add user info to request state
            request.state.user = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "roles": payload.get("roles", []),
            }

        except (JWTError, ValueError) as e:
            logger.warning(f"Invalid token: {e}")
            return Response(
                content='{"detail": "Invalid or expired token"}',
                status_code=401,
                media_type="application/json",
            )

        response = await call_next(request)
        return response


def create_access_token(
    user_id: str,
    email: str,
    roles: Optional[list] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a new JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode = {
        "sub": user_id,
        "email": email,
        "roles": roles or [],
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    """Create a new JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=7)

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


class PermissionChecker:
    """Check user permissions"""

    def __init__(self, required_roles: list):
        self.required_roles = required_roles

    def __call__(self, request: Request):
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )

        user_roles = set(user.get("roles", []))
        if not any(role in user_roles for role in self.required_roles):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

        return user
