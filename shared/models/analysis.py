"""
Shared models for analysis results
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    """Analysis job status"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisType(str, Enum):
    """Types of analysis"""

    SECURITY = "security"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    TAINT = "taint"
    COMPREHENSIVE = "comprehensive"


class Severity(str, Enum):
    """Severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(BaseModel):
    """Base finding model"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    rule_id: str
    rule_name: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    message: str
    file_path: str
    line_start: int
    line_end: int
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    explanation: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    references: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SecurityFinding(Finding):
    """Security-specific finding"""

    vulnerability_type: str
    exploitability: Optional[str] = None
    impact: Optional[str] = None
    remediation_effort: Optional[str] = None


class PerformanceFinding(Finding):
    """Performance-specific finding"""

    metric: str  # time, memory, cpu, etc.
    current_value: Optional[str] = None
    target_value: Optional[str] = None
    expected_improvement: Optional[str] = None
    complexity_score: Optional[float] = None


class QualityFinding(Finding):
    """Code quality finding"""

    category: str  # complexity, style, maintainability, etc.
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


class AnalysisMetrics(BaseModel):
    """Analysis metrics"""

    files_analyzed: int = 0
    lines_analyzed: int = 0
    findings_total: int = 0
    findings_by_severity: Dict[Severity, int] = Field(default_factory=dict)
    analysis_time_ms: int = 0


class AnalysisResult(BaseModel):
    """Analysis result model"""

    id: UUID = Field(default_factory=uuid4)
    repo_id: str
    analysis_type: AnalysisType
    status: AnalysisStatus
    findings: List[Finding] = Field(default_factory=list)
    metrics: AnalysisMetrics = Field(default_factory=AnalysisMetrics)
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AnalysisJob(BaseModel):
    """Analysis job model"""

    id: UUID = Field(default_factory=uuid4)
    repo_id: str
    repo_url: str
    branch: str = "main"
    analysis_types: List[AnalysisType]
    status: AnalysisStatus = AnalysisStatus.PENDING
    priority: int = 5  # 1-10, lower is higher priority
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    result_id: Optional[UUID] = None
    error_message: Optional[str] = None
    options: Optional[Dict] = None
