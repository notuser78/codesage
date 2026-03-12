"""
Analysis Engine configuration
"""

from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Analysis engine settings"""
    
    # Application
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    
    # Database
    DATABASE_URL: str = "postgresql://codesage:codesage_secret@localhost:5432/codesage"
    
    # Redis
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"
    
    # RabbitMQ / Celery
    RABBITMQ_URL: str = "amqp://codesage:rabbitmq_secret@localhost:5672/"
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_ACKS_LATE: bool = True
    
    # Service URLs
    LLM_SERVICE_URL: str = "http://localhost:8001"
    KNOWLEDGE_SERVICE_URL: str = "http://localhost:8002"
    
    # Analysis Settings
    MAX_ANALYSIS_TIME: int = 300  # 5 minutes
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_FILES_PER_ANALYSIS: int = 1000
    SUPPORTED_LANGUAGES: List[str] = [
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "rust",
        "cpp",
        "c",
        "csharp",
        "php",
        "ruby",
    ]
    
    # Security Scanner
    ENABLE_SEMGREP: bool = True
    ENABLE_BANDIT: bool = True
    SEMGREP_RULES: List[str] = [
        "p/security-audit",
        "p/owasp-top-ten",
        "p/cwe-top-25",
    ]
    
    # Performance Analyzer
    COMPLEXITY_THRESHOLD_HIGH: int = 15
    COMPLEXITY_THRESHOLD_MEDIUM: int = 10
    MAX_FUNCTION_LINES: int = 50
    
    # Taint Analysis
    ENABLE_TAINT_ANALYSIS: bool = True
    TAINT_SOURCES: List[str] = [
        "request.args",
        "request.form",
        "request.json",
        "request.headers",
        "input",
        "raw_input",
        "sys.argv",
        "os.environ",
    ]
    TAINT_SINKS: List[str] = [
        "eval",
        "exec",
        "subprocess.call",
        "os.system",
        "cursor.execute",
        "render_template_string",
    ]
    
    # Feature Flags
    ENABLE_SECURITY_SCANNING: bool = True
    ENABLE_PERFORMANCE_ANALYSIS: bool = True
    ENABLE_TAINT_ANALYSIS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


settings = Settings()
