"""
Security scanner for detecting vulnerabilities
Integrates multiple scanning tools and custom rules
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import structlog

from engine.ast_parser import ASTParser, get_parser, ParsedFile

logger = structlog.get_logger()


@dataclass
class SecurityFinding:
    """A security vulnerability finding"""

    rule_id: str
    rule_name: str
    severity: str  # critical, high, medium, low, info
    confidence: str  # high, medium, low
    message: str
    file_path: str
    line_start: int
    line_end: int
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    code_snippet: Optional[str] = None
    remediation: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result of a security scan"""

    findings: List[SecurityFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    scan_time_ms: int = 0
    files_scanned: int = 0
    rules_applied: int = 0


class SecurityScanner:
    """Security vulnerability scanner"""

    # OWASP Top 10 mapping
    OWASP_CATEGORIES = {
        "A01": "Broken Access Control",
        "A02": "Cryptographic Failures",
        "A03": "Injection",
        "A04": "Insecure Design",
        "A05": "Security Misconfiguration",
        "A06": "Vulnerable and Outdated Components",
        "A07": "Identification and Authentication Failures",
        "A08": "Software and Data Integrity Failures",
        "A09": "Security Logging and Monitoring Failures",
        "A10": "Server-Side Request Forgery",
    }

    # CWE to OWASP mapping
    CWE_TO_OWASP = {
        "CWE-89": "A03",  # SQL Injection
        "CWE-78": "A03",  # OS Command Injection
        "CWE-79": "A03",  # XSS
        "CWE-94": "A03",  # Code Injection
        "CWE-22": "A01",  # Path Traversal
        "CWE-312": "A02",  # Cleartext Storage
        "CWE-798": "A07",  # Hardcoded Credentials
        "CWE-307": "A07",  # Brute Force
        "CWE-502": "A08",  # Deserialization
        "CWE-918": "A10",  # SSRF
    }

    def __init__(self):
        self.parser = get_parser()
        self.custom_rules = self._load_custom_rules()

    def _load_custom_rules(self) -> List[Dict]:
        """Load custom security rules"""
        return [
            {
                "id": "CS-S001",
                "name": "SQL Injection Risk",
                "pattern": r'(?:execute|query|cursor\.execute)\s*\(\s*["\'].*%s',
                "severity": "high",
                "confidence": "medium",
                "message": "Potential SQL injection vulnerability detected",
                "remediation": "Use parameterized queries instead of string formatting",
                "cwe_id": "CWE-89",
                "languages": ["python"],
            },
            {
                "id": "CS-S002",
                "name": "Hardcoded Secret",
                "pattern": r'(?:password|secret|token|key|api_key)\s*=\s*["\'][^"\']{8,}["\']',
                "severity": "high",
                "confidence": "low",
                "message": "Potential hardcoded secret detected",
                "remediation": "Use environment variables or a secrets manager",
                "cwe_id": "CWE-798",
                "languages": ["*"],
            },
            {
                "id": "CS-S003",
                "name": "Insecure Deserialization",
                "pattern": r"(?:pickle\.loads|yaml\.load|eval|exec)\s*\(",
                "severity": "critical",
                "confidence": "high",
                "message": "Insecure deserialization detected",
                "remediation": "Use safe alternatives like json.loads or yaml.safe_load",
                "cwe_id": "CWE-502",
                "languages": ["python"],
            },
            {
                "id": "CS-S004",
                "name": "Command Injection Risk",
                "pattern": r"(?:os\.system|subprocess\.call|subprocess\.Popen)\s*\([^)]*%",
                "severity": "critical",
                "confidence": "medium",
                "message": "Potential command injection vulnerability",
                "remediation": "Use subprocess with list arguments instead of shell=True",
                "cwe_id": "CWE-78",
                "languages": ["python"],
            },
            {
                "id": "CS-S005",
                "name": "Weak Cryptography",
                "pattern": r"(?:md5|sha1)\s*\(",
                "severity": "medium",
                "confidence": "medium",
                "message": "Use of weak cryptographic algorithm",
                "remediation": "Use SHA-256 or stronger hashing algorithms",
                "cwe_id": "CWE-328",
                "languages": ["python", "javascript", "java"],
            },
            {
                "id": "CS-S006",
                "name": "Debug Mode Enabled",
                "pattern": r"DEBUG\s*=\s*True",
                "severity": "medium",
                "confidence": "high",
                "message": "Debug mode should not be enabled in production",
                "remediation": "Set DEBUG = False in production configuration",
                "cwe_id": "CWE-489",
                "languages": ["python"],
            },
            {
                "id": "CS-S007",
                "name": "XSS Vulnerability",
                "pattern": r"(?:innerHTML|outerHTML|document\.write)\s*=\s*",
                "severity": "high",
                "confidence": "medium",
                "message": "Potential XSS vulnerability",
                "remediation": "Use textContent or sanitize user input before DOM insertion",
                "cwe_id": "CWE-79",
                "languages": ["javascript"],
            },
            {
                "id": "CS-S008",
                "name": "Insecure CORS",
                "pattern": r"Access-Control-Allow-Origin.*\*",
                "severity": "low",
                "confidence": "high",
                "message": "Permissive CORS policy detected",
                "remediation": "Specify explicit allowed origins instead of wildcard",
                "cwe_id": "CWE-942",
                "languages": ["*"],
            },
        ]

    def scan_file(self, file_path: str, content: Optional[str] = None) -> ScanResult:
        """Scan a single file for security issues"""
        import time

        start_time = time.time()

        findings = []
        errors = []

        try:
            # Parse the file
            parsed = self.parser.parse_file(file_path, content)

            if parsed.errors:
                errors.extend(parsed.errors)

            if parsed.language == "unknown":
                return ScanResult(errors=errors)

            # Run custom rule-based scanning
            rule_findings = self._scan_with_rules(file_path, content, parsed.language)
            findings.extend(rule_findings)

            # Run AST-based analysis
            ast_findings = self._scan_ast(parsed)
            findings.extend(ast_findings)

            # Run Semgrep if available
            if self._is_semgrep_available():
                semgrep_findings = self._run_semgrep(file_path)
                findings.extend(semgrep_findings)

            # Run Bandit for Python files
            if parsed.language == "python" and self._is_bandit_available():
                bandit_findings = self._run_bandit(file_path)
                findings.extend(bandit_findings)

        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            errors.append(str(e))

        scan_time_ms = int((time.time() - start_time) * 1000)

        return ScanResult(
            findings=findings,
            errors=errors,
            scan_time_ms=scan_time_ms,
            files_scanned=1,
            rules_applied=len(self.custom_rules),
        )

    def scan_directory(
        self, directory: str, include_patterns: Optional[List[str]] = None
    ) -> ScanResult:
        """Scan a directory for security issues"""
        import time

        start_time = time.time()

        all_findings = []
        all_errors = []
        files_scanned = 0

        path = Path(directory)

        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if file should be included
            if include_patterns:
                if not any(file_path.match(pattern) for pattern in include_patterns):
                    continue

            # Skip certain directories
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if "node_modules" in file_path.parts or "__pycache__" in file_path.parts:
                continue

            result = self.scan_file(str(file_path))
            all_findings.extend(result.findings)
            all_errors.extend(result.errors)
            files_scanned += 1

        scan_time_ms = int((time.time() - start_time) * 1000)

        return ScanResult(
            findings=all_findings,
            errors=all_errors,
            scan_time_ms=scan_time_ms,
            files_scanned=files_scanned,
            rules_applied=len(self.custom_rules),
        )

    def _scan_with_rules(
        self, file_path: str, content: Optional[str], language: str
    ) -> List[SecurityFinding]:
        """Scan file using custom regex rules"""
        findings = []

        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                return findings

        lines = content.split("\n")

        for rule in self.custom_rules:
            # Check if rule applies to this language
            if rule["languages"] != ["*"] and language not in rule["languages"]:
                continue

            try:
                pattern = re.compile(rule["pattern"], re.IGNORECASE)

                for line_num, line in enumerate(lines, 1):
                    matches = pattern.finditer(line)

                    for match in matches:
                        finding = SecurityFinding(
                            rule_id=rule["id"],
                            rule_name=rule["name"],
                            severity=rule["severity"],
                            confidence=rule["confidence"],
                            message=rule["message"],
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            column_start=match.start(),
                            column_end=match.end(),
                            code_snippet=line.strip(),
                            remediation=rule.get("remediation"),
                            cwe_id=rule.get("cwe_id"),
                            owasp_category=self.CWE_TO_OWASP.get(rule.get("cwe_id")),
                        )
                        findings.append(finding)

            except re.error as e:
                logger.warning(f"Invalid regex in rule {rule['id']}: {e}")

        return findings

    def _scan_ast(self, parsed: ParsedFile) -> List[SecurityFinding]:
        """Scan using AST analysis"""
        findings = []

        # Check for dangerous function calls
        dangerous_functions = {
            "python": ["eval", "exec", "compile", "__import__"],
            "javascript": ["eval", "Function", "setTimeout", "setInterval"],
            "java": ["Runtime.exec", "ProcessBuilder"],
        }

        if parsed.language in dangerous_functions:
            for func in parsed.functions:
                if func.name in dangerous_functions[parsed.language]:
                    finding = SecurityFinding(
                        rule_id="CS-AST001",
                        rule_name="Dangerous Function Usage",
                        severity="high",
                        confidence="medium",
                        message=f"Potentially dangerous function '{func.name}' detected",
                        file_path=parsed.file_path,
                        line_start=func.start_line,
                        line_end=func.end_line,
                        remediation="Avoid using dangerous functions; use safer alternatives",
                        cwe_id="CWE-94",
                        owasp_category="A03",
                    )
                    findings.append(finding)

        return findings

    def _is_semgrep_available(self) -> bool:
        """Check if Semgrep is installed"""
        try:
            subprocess.run(["semgrep", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _run_semgrep(self, file_path: str) -> List[SecurityFinding]:
        """Run Semgrep scan"""
        findings = []

        try:
            result = subprocess.run(
                [
                    "semgrep",
                    "--config=p/security-audit",
                    "--config=p/owasp-top-ten",
                    "--json",
                    "--quiet",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode in (0, 1):  # 1 means findings found
                output = json.loads(result.stdout)

                for match in output.get("results", []):
                    finding = SecurityFinding(
                        rule_id=match.get("check_id", "unknown"),
                        rule_name=match.get("extra", {}).get("message", "Unknown"),
                        severity=self._map_semgrep_severity(
                            match.get("extra", {}).get("severity", "WARNING")
                        ),
                        confidence="medium",
                        message=match.get("extra", {}).get("message", ""),
                        file_path=match.get("path", file_path),
                        line_start=match.get("start", {}).get("line", 0),
                        line_end=match.get("end", {}).get("line", 0),
                        code_snippet=match.get("extra", {}).get("lines", ""),
                    )
                    findings.append(finding)

        except subprocess.TimeoutExpired:
            logger.warning(f"Semgrep timeout for {file_path}")
        except Exception as e:
            logger.error(f"Semgrep error: {e}")

        return findings

    def _is_bandit_available(self) -> bool:
        """Check if Bandit is installed"""
        try:
            subprocess.run(["bandit", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _run_bandit(self, file_path: str) -> List[SecurityFinding]:
        """Run Bandit scan for Python files"""
        findings = []

        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.stdout:
                output = json.loads(result.stdout)

                for issue in output.get("results", []):
                    finding = SecurityFinding(
                        rule_id=issue.get("test_id", "B000"),
                        rule_name=issue.get("test_name", "Unknown"),
                        severity=issue.get("issue_severity", "LOW").lower(),
                        confidence=issue.get("issue_confidence", "MEDIUM").lower(),
                        message=issue.get("issue_text", ""),
                        file_path=issue.get("filename", file_path),
                        line_start=issue.get("line_number", 0),
                        line_end=issue.get("line_number", 0),
                        code_snippet=issue.get("code", ""),
                        cwe_id=issue.get("cwe", ""),
                    )
                    findings.append(finding)

        except subprocess.TimeoutExpired:
            logger.warning(f"Bandit timeout for {file_path}")
        except Exception as e:
            logger.error(f"Bandit error: {e}")

        return findings

    def _map_semgrep_severity(self, severity: str) -> str:
        """Map Semgrep severity to our severity levels"""
        mapping = {
            "ERROR": "high",
            "WARNING": "medium",
            "INFO": "low",
        }
        return mapping.get(severity.upper(), "medium")


# Global scanner instance
_scanner: Optional[SecurityScanner] = None


def get_scanner() -> SecurityScanner:
    """Get or create global scanner instance"""
    global _scanner
    if _scanner is None:
        _scanner = SecurityScanner()
    return _scanner
