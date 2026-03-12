"""
Database connection management
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

logger = structlog.get_logger()

# SQLAlchemy async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Redis connection pool
redis_pool: Optional[aioredis.Redis] = None


async def init_db():
    """Initialize database connections"""
    global redis_pool
    
    # Test database connection
    async with engine.begin() as conn:
        await conn.execute("SELECT 1")
    logger.info("Database connection established")
    
    # Initialize Redis
    redis_pool = aioredis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_POOL_SIZE,
        decode_responses=True,
    )
    await redis_pool.ping()
    logger.info("Redis connection established")


async def close_db():
    """Close database connections"""
    global redis_pool
    
    await engine.dispose()
    logger.info("Database connection closed")
    
    if redis_pool:
        await redis_pool.close()
        logger.info("Redis connection closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session as async context manager"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis() -> aioredis.Redis:
    """Get Redis connection"""
    if redis_pool is None:
        raise RuntimeError("Redis not initialized")
    return redis_pool


class DatabaseManager:
    """Database manager for advanced operations"""
    
    @staticmethod
    async def health_check() -> dict:
        """Check database health"""
        health = {
            "database": False,
            "redis": False,
        }
        
        # Check PostgreSQL
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            health["database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Check Redis
        try:
            if redis_pool:
                await redis_pool.ping()
                health["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        
        return health
    
    @staticmethod
    async def execute_with_retry(func, max_retries: int = 3, delay: float = 1.0):
        """Execute database function with retry logic"""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(delay * (2 ** attempt))
