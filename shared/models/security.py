"""
Shared models for security analysis
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CVSSScore(BaseModel):
    """CVSS vulnerability score"""

    score: float = Field(ge=0, le=10)
    vector: str
    severity: str  # None, Low, Medium, High, Critical


class Vulnerability(BaseModel):
    """Security vulnerability"""

    id: str
    cwe_id: Optional[str] = None
    cwe_name: Optional[str] = None
    cve_id: Optional[str] = None
    name: str
    description: str
    severity: str
    cvss: Optional[CVSSScore] = None
    remediation: Optional[str] = None
    references: List[str] = Field(default_factory=list)


class SecurityRule(BaseModel):
    """Security analysis rule"""

    id: str
    name: str
    description: str
    category: str  # injection, xss, auth, crypto, etc.
    severity: str
    languages: List[str]
    cwe_ids: List[str] = Field(default_factory=list)
    owasp_categories: List[str] = Field(default_factory=list)
    pattern: Optional[str] = None  # regex or AST pattern
    enabled: bool = True


class SecurityPolicy(BaseModel):
    """Security policy configuration"""

    name: str
    description: str
    rules: List[str]  # rule IDs
    severity_threshold: str = "low"  # minimum severity to report
    confidence_threshold: float = 0.5
    exclude_patterns: List[str] = Field(default_factory=list)
    include_patterns: List[str] = Field(default_factory=list)


class TaintSource(BaseModel):
    """Taint analysis source"""

    name: str
    source_type: str  # user_input, file, network, etc.
    taint_level: str  # low, medium, high, critical
    description: str


class TaintSink(BaseModel):
    """Taint analysis sink"""

    name: str
    sink_type: str  # sql, command, xss, etc.
    required_taint_level: str
    description: str


class TaintFlow(BaseModel):
    """Taint flow from source to sink"""

    source: TaintSource
    sink: TaintSink
    path: List[Dict]  # intermediate steps
    is_sanitized: bool = False
    sanitizers: List[str] = Field(default_factory=list)


class SecurityReport(BaseModel):
    """Security analysis report"""

    repo_id: str
    analysis_id: str
    summary: str
    vulnerabilities: List[Vulnerability]
    findings_by_severity: Dict[str, int]
    findings_by_category: Dict[str, int]
    top_vulnerabilities: List[Vulnerability]
    remediation_priority: List[str]  # ordered list of fixes
    compliance_status: Dict[str, bool]  # standard -> compliant
