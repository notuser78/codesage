"""
Celery tasks for analysis operations
"""

import time
from typing import Dict, List, Optional
from uuid import UUID

import httpx
import structlog
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import settings
from engine.ast_parser import get_parser
from engine.performance_analyzer import get_analyzer
from engine.security_scanner import get_scanner
from engine.taint_analysis import get_taint_analyzer

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=3)
def analyze_repository(
    self,
    repo_id: str,
    repo_url: str,
    branch: str = "main",
    analysis_types: List[str] = None,
    options: Optional[Dict] = None,
):
    """
    Analyze an entire repository

    Args:
        repo_id: Repository ID
        repo_url: Repository URL
        branch: Branch to analyze
        analysis_types: Types of analysis to perform
        options: Additional analysis options
    """
    analysis_types = analysis_types or ["security", "performance"]
    options = options or {}

    logger.info(
        "Starting repository analysis",
        repo_id=repo_id,
        repo_url=repo_url,
        branch=branch,
        analysis_types=analysis_types,
    )

    start_time = time.time()

    try:
        # Clone repository (simplified - in production, use proper git operations)
        repo_path = f"/tmp/repos/{repo_id}"

        # Perform analysis
        results = {
            "repo_id": repo_id,
            "analysis_types": analysis_types,
            "security": None,
            "performance": None,
            "taint": None,
            "errors": [],
        }

        if "security" in analysis_types:
            security_result = analyze_security.delay(repo_path, options.get("security", {}))
            results["security"] = security_result.get()

        if "performance" in analysis_types:
            performance_result = analyze_performance.delay(
                repo_path, options.get("performance", {})
            )
            results["performance"] = performance_result.get()

        if "taint" in analysis_types and settings.ENABLE_TAINT_ANALYSIS:
            taint_result = analyze_taint.delay(repo_path, options.get("taint", {}))
            results["taint"] = taint_result.get()

        duration = time.time() - start_time

        # Notify knowledge graph service
        try:
            notify_knowledge_service(repo_id, results)
        except Exception as e:
            logger.error(f"Failed to notify knowledge service: {e}")

        logger.info(
            "Repository analysis completed",
            repo_id=repo_id,
            duration_seconds=duration,
        )

        return {
            "status": "completed",
            "repo_id": repo_id,
            "duration_seconds": duration,
            "results": results,
        }

    except Exception as exc:
        logger.error(f"Repository analysis failed: {exc}")

        # Retry with exponential backoff
        try:
            self.retry(countdown=60 * (2**self.request.retries), exc=exc)
        except MaxRetriesExceededError:
            return {
                "status": "failed",
                "repo_id": repo_id,
                "error": str(exc),
            }


@shared_task(bind=True, max_retries=3)
def analyze_file(
    self,
    file_path: str,
    analysis_types: List[str] = None,
    options: Optional[Dict] = None,
):
    """Analyze a single file"""
    analysis_types = analysis_types or ["security", "performance"]
    options = options or {}

    logger.info(
        "Analyzing file",
        file_path=file_path,
        analysis_types=analysis_types,
    )

    results = {
        "file_path": file_path,
        "analysis_types": analysis_types,
    }

    try:
        if "security" in analysis_types:
            scanner = get_scanner()
            result = scanner.scan_file(file_path)
            results["security"] = {
                "findings_count": len(result.findings),
                "findings": [
                    {
                        "rule_id": f.rule_id,
                        "severity": f.severity,
                        "message": f.message,
                        "line": f.line_start,
                    }
                    for f in result.findings
                ],
            }

        if "performance" in analysis_types:
            analyzer = get_analyzer()
            result = analyzer.analyze_file(file_path)
            results["performance"] = {
                "findings_count": len(result.findings),
                "metrics": {
                    name: {
                        "cyclomatic_complexity": m.cyclomatic_complexity,
                        "maintainability_index": m.maintainability_index,
                    }
                    for name, m in result.metrics.items()
                },
            }

        return results

    except Exception as exc:
        logger.error(f"File analysis failed: {exc}")
        self.retry(countdown=30, exc=exc)


@shared_task
def analyze_security(repo_path: str, options: Optional[Dict] = None) -> Dict:
    """Perform security analysis on a repository"""
    options = options or {}

    logger.info("Starting security analysis", repo_path=repo_path)

    scanner = get_scanner()
    result = scanner.scan_directory(repo_path)

    return {
        "status": "completed",
        "findings_count": len(result.findings),
        "findings": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity,
                "confidence": f.confidence,
                "message": f.message,
                "file_path": f.file_path,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "cwe_id": f.cwe_id,
                "owasp_category": f.owasp_category,
            }
            for f in result.findings
        ],
        "files_scanned": result.files_scanned,
        "scan_time_ms": result.scan_time_ms,
    }


@shared_task
def analyze_performance(repo_path: str, options: Optional[Dict] = None) -> Dict:
    """Perform performance analysis on a repository"""
    options = options or {}

    logger.info("Starting performance analysis", repo_path=repo_path)

    analyzer = get_analyzer()

    from pathlib import Path

    all_findings = []
    all_metrics = {}
    files_analyzed = 0

    for file_path in Path(repo_path).rglob("*"):
        if not file_path.is_file():
            continue

        try:
            result = analyzer.analyze_file(str(file_path))
            all_findings.extend(result.findings)
            all_metrics.update(result.metrics)
            files_analyzed += 1
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")

    return {
        "status": "completed",
        "findings_count": len(all_findings),
        "findings": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity,
                "message": f.message,
                "file_path": f.file_path,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "complexity_score": f.complexity_score,
            }
            for f in all_findings[:100]  # Limit results
        ],
        "hot_paths": (
            analyzer.get_hot_paths(str(Path(repo_path) / "src"))
            if (Path(repo_path) / "src").exists()
            else []
        ),
        "files_analyzed": files_analyzed,
    }


@shared_task
def analyze_taint(repo_path: str, options: Optional[Dict] = None) -> Dict:
    """Perform taint analysis on a repository"""
    options = options or {}

    logger.info("Starting taint analysis", repo_path=repo_path)

    analyzer = get_taint_analyzer()

    from pathlib import Path

    all_findings = []
    files_analyzed = 0

    for file_path in Path(repo_path).rglob("*"):
        if not file_path.is_file():
            continue

        try:
            result = analyzer.analyze_file(str(file_path))
            all_findings.extend(result.findings)
            files_analyzed += 1
        except Exception as e:
            logger.warning(f"Failed taint analysis of {file_path}: {e}")

    return {
        "status": "completed",
        "findings_count": len(all_findings),
        "findings": [
            {
                "vulnerability_type": f.vulnerability_type,
                "severity": f.severity,
                "message": f.message,
                "file_path": f.file_path,
                "source_line": f.source.line,
                "sink_line": f.sink.line,
                "cwe_id": f.cwe_id,
            }
            for f in all_findings[:100]
        ],
        "files_analyzed": files_analyzed,
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def notify_knowledge_service(repo_id: str, analysis_results: Dict):
    """Notify knowledge graph service of analysis results"""
    try:
        response = httpx.post(
            f"{settings.KNOWLEDGE_SERVICE_URL}/api/v1/index",
            json={
                "repo_id": repo_id,
                "analysis_results": analysis_results,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        logger.info("Knowledge service notified", repo_id=repo_id)
    except Exception as e:
        logger.error(f"Failed to notify knowledge service: {e}")
        raise


@shared_task
def cleanup_old_analyses(max_age_days: int = 30):
    """Clean up old analysis results"""
    logger.info("Cleaning up old analyses", max_age_days=max_age_days)

    # This would delete old records from database
    # Implementation depends on your data retention policy

    return {"status": "completed", "deleted_count": 0}


@shared_task
def generate_analysis_report(repo_id: str, format: str = "json") -> Dict:
    """Generate a comprehensive analysis report"""
    logger.info("Generating analysis report", repo_id=repo_id, format=format)

    # Fetch analysis results from database
    # Generate report in requested format

    return {
        "status": "completed",
        "repo_id": repo_id,
        "format": format,
        "report_url": f"/reports/{repo_id}.{format}",
    }
