"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, get_redis, redis_pool

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    services: dict


class ReadinessResponse(BaseModel):
    ready: bool
    checks: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        services={"api": "up"},
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check for Kubernetes"""
    checks = {
        "database": False,
        "redis": False,
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    # Check Redis
    try:
        if redis_pool:
            await redis_pool.ping()
            checks["redis"] = True
    except Exception:
        pass

    all_ready = all(checks.values())

    return ReadinessResponse(
        ready=all_ready,
        checks=checks,
    )


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # This would be handled by prometheus-client in production
    return {"metrics": "available"}
