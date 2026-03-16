"""
Analysis endpoints
"""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import PermissionChecker

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models
class CodeSnippet(BaseModel):
    code: str = Field(..., min_length=1, max_length=100000)
    language: str
    filename: Optional[str] = None


class AnalysisOptions(BaseModel):
    include_suggestions: bool = True
    include_explanations: bool = True
    severity_threshold: str = "low"
    max_findings: int = 100


class AnalysisRequest(BaseModel):
    snippet: CodeSnippet
    analysis_types: List[str] = Field(default_factory=lambda: ["security", "performance"])
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class Finding(BaseModel):
    id: str
    type: str
    severity: str
    message: str
    line_start: int
    line_end: int
    column_start: Optional[int]
    column_end: Optional[int]
    file_path: Optional[str]
    code_snippet: Optional[str]
    suggestion: Optional[str]
    explanation: Optional[str]
    cwe_id: Optional[str]
    confidence: float


class AnalysisMetrics(BaseModel):
    complexity_score: Optional[float]
    maintainability_index: Optional[float]
    lines_of_code: int
    cyclomatic_complexity: Optional[int]
    cognitive_complexity: Optional[int]


class AnalysisResponse(BaseModel):
    id: UUID
    status: str
    analysis_types: List[str]
    findings: List[Finding]
    metrics: Optional[AnalysisMetrics]
    summary: dict
    completed_at: Optional[str]
    duration_ms: Optional[int]


class BatchAnalysisRequest(BaseModel):
    snippets: List[CodeSnippet]
    analysis_types: List[str] = Field(default_factory=lambda: ["security", "performance"])


# Mock analysis results for demo
mock_findings = [
    {
        "id": "finding-001",
        "type": "security",
        "severity": "high",
        "message": "Potential SQL injection vulnerability detected",
        "line_start": 15,
        "line_end": 15,
        "column_start": 20,
        "column_end": 45,
        "file_path": "src/database.py",
        "code_snippet": 'query = f"SELECT * FROM users WHERE id = {user_id}"',
        "suggestion": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
        "explanation": "String interpolation in SQL queries can lead to SQL injection attacks.",
        "cwe_id": "CWE-89",
        "confidence": 0.95,
    },
    {
        "id": "finding-002",
        "type": "performance",
        "severity": "medium",
        "message": "Inefficient list concatenation in loop",
        "line_start": 42,
        "line_end": 44,
        "column_start": 8,
        "column_end": 25,
        "file_path": "src/processing.py",
        "code_snippet": "result = []\nfor item in items:\n    result = result + [process(item)]",
        "suggestion": "Use list.append() or list comprehension for better performance",
        "explanation": "Using + to concatenate lists creates a new list each iteration, O(n^2) complexity.",
        "cwe_id": None,
        "confidence": 0.88,
    },
]


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_code(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(PermissionChecker(["user"])),
):
    """Analyze a code snippet"""
    import uuid
    from datetime import datetime

    analysis_id = uuid.uuid4()
    start_time = datetime.utcnow()

    logger.info(
        "Analysis requested",
        analysis_id=str(analysis_id),
        language=request.snippet.language,
        analysis_types=request.analysis_types,
    )

    # This would call the analysis service in production
    # For demo, return mock results
    findings = [Finding(**f) for f in mock_findings if f["type"] in request.analysis_types]

    completed_at = datetime.utcnow()
    duration_ms = int((completed_at - start_time).total_seconds() * 1000)

    # Calculate summary
    severity_counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
    type_counts = {"security": 0, "performance": 0, "quality": 0}

    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        type_counts[finding.type] = type_counts.get(finding.type, 0) + 1

    return AnalysisResponse(
        id=analysis_id,
        status="completed",
        analysis_types=request.analysis_types,
        findings=findings,
        metrics=AnalysisMetrics(
            complexity_score=7.5,
            maintainability_index=82.3,
            lines_of_code=len(request.snippet.code.split("\n")),
            cyclomatic_complexity=12,
            cognitive_complexity=8,
        ),
        summary={
            "total_findings": len(findings),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
        },
        completed_at=completed_at.isoformat(),
        duration_ms=duration_ms,
    )


@router.post("/analyze/batch")
async def analyze_batch(
    request: BatchAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(PermissionChecker(["user"])),
):
    """Analyze multiple code snippets"""
    import uuid
    from datetime import datetime

    batch_id = uuid.uuid4()

    logger.info(
        "Batch analysis requested",
        batch_id=str(batch_id),
        snippet_count=len(request.snippets),
    )

    results = []
    for snippet in request.snippets:
        # Mock analysis for each snippet
        results.append(
            {
                "filename": snippet.filename,
                "language": snippet.language,
                "findings_count": 2,
                "status": "completed",
            }
        )

    return {
        "batch_id": str(batch_id),
        "status": "completed",
        "results": results,
        "completed_at": datetime.utcnow().isoformat(),
    }


@router.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis_result(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(PermissionChecker(["user"])),
):
    """Get analysis results by ID"""
    # This would fetch from database in production
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Analysis result retrieval not yet implemented",
    )


@router.get("/analysis/{analysis_id}/findings")
async def get_analysis_findings(
    analysis_id: UUID,
    severity: Optional[str] = None,
    finding_type: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(PermissionChecker(["user"])),
):
    """Get findings for an analysis with filtering"""
    # Mock findings
    findings = mock_findings

    if severity:
        findings = [f for f in findings if f["severity"] == severity]
    if finding_type:
        findings = [f for f in findings if f["type"] == finding_type]

    total = len(findings)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "analysis_id": str(analysis_id),
        "findings": findings[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/analysis/{analysis_id}/regenerate")
async def regenerate_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(PermissionChecker(["user"])),
):
    """Regenerate analysis with updated rules/models"""
    logger.info("Regenerating analysis", analysis_id=str(analysis_id))

    return {
        "analysis_id": str(analysis_id),
        "status": "queued",
        "message": "Analysis regeneration queued",
    }


@router.get("/rules")
async def list_analysis_rules(
    category: Optional[str] = None,
    language: Optional[str] = None,
    current_user: dict = Depends(PermissionChecker(["user"])),
):
    """List available analysis rules"""
    rules = [
        {
            "id": "sql-injection",
            "name": "SQL Injection Detection",
            "category": "security",
            "languages": ["python", "javascript", "java", "php"],
            "severity": "high",
            "description": "Detects potential SQL injection vulnerabilities",
        },
        {
            "id": "xss-detection",
            "name": "XSS Detection",
            "category": "security",
            "languages": ["javascript", "php", "python"],
            "severity": "high",
            "description": "Detects potential cross-site scripting vulnerabilities",
        },
        {
            "id": "inefficient-loop",
            "name": "Inefficient Loop Pattern",
            "category": "performance",
            "languages": ["python", "javascript"],
            "severity": "medium",
            "description": "Detects inefficient patterns in loops",
        },
        {
            "id": "complex-function",
            "name": "Overly Complex Function",
            "category": "quality",
            "languages": ["*"],
            "severity": "low",
            "description": "Detects functions with high cyclomatic complexity",
        },
    ]

    if category:
        rules = [r for r in rules if r["category"] == category]
    if language:
        rules = [r for r in rules if language in r["languages"] or "*" in r["languages"]]

    return {"rules": rules, "total": len(rules)}


@router.get("/languages")
async def supported_languages(
    current_user: dict = Depends(PermissionChecker(["user"])),
):
    """Get list of supported programming languages"""
    return {
        "languages": [
            {"id": "python", "name": "Python", "extensions": [".py"]},
            {"id": "javascript", "name": "JavaScript", "extensions": [".js", ".jsx"]},
            {"id": "typescript", "name": "TypeScript", "extensions": [".ts", ".tsx"]},
            {"id": "java", "name": "Java", "extensions": [".java"]},
            {"id": "go", "name": "Go", "extensions": [".go"]},
            {"id": "rust", "name": "Rust", "extensions": [".rs"]},
            {"id": "cpp", "name": "C++", "extensions": [".cpp", ".cc", ".hpp"]},
            {"id": "c", "name": "C", "extensions": [".c", ".h"]},
            {"id": "csharp", "name": "C#", "extensions": [".cs"]},
            {"id": "php", "name": "PHP", "extensions": [".php"]},
            {"id": "ruby", "name": "Ruby", "extensions": [".rb"]},
            {"id": "swift", "name": "Swift", "extensions": [".swift"]},
        ]
    }
