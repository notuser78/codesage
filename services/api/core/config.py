"""
Application configuration
Uses pydantic-settings for environment-based configuration
"""

from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "CodeSage API"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = "postgresql://codesage:codesage_secret@localhost:5432/codesage"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j_secret"
    
    # Weaviate
    WEAVIATE_URL: str = "http://localhost:8080"
    
    # RabbitMQ / Celery
    RABBITMQ_URL: str = "amqp://codesage:rabbitmq_secret@localhost:5672/"
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_ACKS_LATE: bool = True
    
    # Service URLs
    LLM_SERVICE_URL: str = "http://localhost:8001"
    KNOWLEDGE_SERVICE_URL: str = "http://localhost:8002"
    
    # JWT
    JWT_SECRET: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Feature Flags
    ENABLE_SECURITY_SCANNING: bool = True
    ENABLE_PERFORMANCE_ANALYSIS: bool = True
    ENABLE_TAINT_ANALYSIS: bool = True
    ENABLE_KNOWLEDGE_GRAPH: bool = True
    ENABLE_VECTOR_SEARCH: bool = True
    
    # External APIs
    GITHUB_TOKEN: Optional[str] = None
    GITLAB_TOKEN: Optional[str] = None
    BITBUCKET_TOKEN: Optional[str] = None
    
    # Monitoring
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp"
    
    # LLM
    DEFAULT_MODEL: str = "codellama-7b"
    MAX_ANALYSIS_TIME: int = 300  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
