"""
Taint analysis for tracking data flow
Identifies potential security vulnerabilities through data flow analysis
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import structlog

from engine.ast_parser import get_parser, ParsedFile

logger = structlog.get_logger()


class TaintLevel(Enum):
    """Taint level classification"""
    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaintSource:
    """A source of tainted data"""
    name: str
    line: int
    column: int
    taint_level: TaintLevel
    source_type: str  # user_input, file_read, network, etc.


@dataclass
class TaintSink:
    """A sink where tainted data can cause harm"""
    name: str
    line: int
    column: int
    sink_type: str  # sql, command, xss, etc.
    required_taint_level: TaintLevel


@dataclass
class TaintFlow:
    """A flow of tainted data from source to sink"""
    source: TaintSource
    sink: TaintSink
    path: List[Tuple[int, int]] = field(default_factory=list)
    sanitizers: List[str] = field(default_factory=list)
    is_vulnerable: bool = True


@dataclass
class TaintFinding:
    """A taint analysis finding"""
    vulnerability_type: str
    severity: str
    message: str
    source: TaintSource
    sink: TaintSink
    file_path: str
    flow_path: List[Tuple[int, int]] = field(default_factory=list)
    remediation: Optional[str] = None
    cwe_id: Optional[str] = None


@dataclass
class TaintResult:
    """Result of taint analysis"""
    findings: List[TaintFinding] = field(default_factory=list)
    sources: List[TaintSource] = field(default_factory=list)
    sinks: List[TaintSink] = field(default_factory=list)
    flows: List[TaintFlow] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class TaintAnalyzer:
    """Taint analysis engine for data flow tracking"""
    
    # Default taint sources by language
    DEFAULT_SOURCES = {
        "python": [
            ("request.args.get", TaintLevel.HIGH, "http_parameter"),
            ("request.form.get", TaintLevel.HIGH, "http_parameter"),
            ("request.json", TaintLevel.HIGH, "http_body"),
            ("request.headers.get", TaintLevel.MEDIUM, "http_header"),
            ("input", TaintLevel.HIGH, "user_input"),
            ("sys.argv", TaintLevel.MEDIUM, "command_line"),
            ("os.environ.get", TaintLevel.LOW, "environment"),
            ("file.read", TaintLevel.MEDIUM, "file_read"),
            ("socket.recv", TaintLevel.HIGH, "network"),
            ("input", TaintLevel.HIGH, "user_input"),
        ],
        "javascript": [
            ("req.query", TaintLevel.HIGH, "http_parameter"),
            ("req.body", TaintLevel.HIGH, "http_body"),
            ("req.params", TaintLevel.HIGH, "http_parameter"),
            ("req.headers", TaintLevel.MEDIUM, "http_header"),
            ("window.location.href", TaintLevel.HIGH, "url_parameter"),
            ("document.cookie", TaintLevel.MEDIUM, "cookie"),
            ("localStorage.getItem", TaintLevel.MEDIUM, "storage"),
            ("prompt", TaintLevel.HIGH, "user_input"),
            ("fetch", TaintLevel.MEDIUM, "network"),
        ],
        "java": [
            ("request.getParameter", TaintLevel.HIGH, "http_parameter"),
            ("request.getHeader", TaintLevel.MEDIUM, "http_header"),
            ("System.getenv", TaintLevel.LOW, "environment"),
            ("Scanner.nextLine", TaintLevel.HIGH, "user_input"),
            ("BufferedReader.readLine", TaintLevel.MEDIUM, "file_read"),
        ],
    }
    
    # Default taint sinks by language
    DEFAULT_SINKS = {
        "python": [
            ("cursor.execute", "sql", TaintLevel.LOW),
            ("execute", "sql", TaintLevel.LOW),
            ("eval", "code_execution", TaintLevel.CRITICAL),
            ("exec", "code_execution", TaintLevel.CRITICAL),
            ("os.system", "command", TaintLevel.LOW),
            ("subprocess.call", "command", TaintLevel.LOW),
            ("subprocess.Popen", "command", TaintLevel.LOW),
            ("render_template_string", "xss", TaintLevel.LOW),
            ("open", "file_write", TaintLevel.MEDIUM),
            ("pickle.loads", "deserialization", TaintLevel.CRITICAL),
            ("yaml.load", "deserialization", TaintLevel.HIGH),
        ],
        "javascript": [
            ("eval", "code_execution", TaintLevel.CRITICAL),
            ("Function", "code_execution", TaintLevel.CRITICAL),
            ("exec", "command", TaintLevel.LOW),
            ("innerHTML", "xss", TaintLevel.LOW),
            ("document.write", "xss", TaintLevel.LOW),
            ("window.location", "open_redirect", TaintLevel.MEDIUM),
            ("fs.writeFile", "file_write", TaintLevel.MEDIUM),
        ],
        "java": [
            ("Statement.execute", "sql", TaintLevel.LOW),
            ("Runtime.exec", "command", TaintLevel.LOW),
            ("ProcessBuilder", "command", TaintLevel.LOW),
            ("ObjectInputStream.readObject", "deserialization", TaintLevel.CRITICAL),
            ("ScriptEngine.eval", "code_execution", TaintLevel.CRITICAL),
        ],
    }
    
    # Sanitization functions
    SANITIZERS = {
        "python": [
            "escape",
            "html.escape",
            "bleach.clean",
            "re.escape",
            "shlex.quote",
            "int",
            "float",
            "str.encode",
        ],
        "javascript": [
            "encodeURIComponent",
            "encodeURI",
            "escapeHtml",
            "DOMPurify.sanitize",
            "he.encode",
        ],
        "java": [
            "HtmlUtils.htmlEscape",
            "URLEncoder.encode",
            "PreparedStatement",
        ],
    }
    
    def __init__(self):
        self.parser = get_parser()
    
    def analyze_file(self, file_path: str, content: Optional[str] = None) -> TaintResult:
        """Perform taint analysis on a file"""
        findings = []
        sources = []
        sinks = []
        flows = []
        errors = []
        
        try:
            # Parse the file
            parsed = self.parser.parse_file(file_path, content)
            
            if parsed.errors:
                errors.extend(parsed.errors)
            
            if parsed.language == "unknown":
                return TaintResult(errors=errors)
            
            # Identify sources
            file_sources = self._identify_sources(parsed)
            sources.extend(file_sources)
            
            # Identify sinks
            file_sinks = self._identify_sinks(parsed)
            sinks.extend(file_sinks)
            
            # Track data flows
            file_flows = self._track_flows(parsed, sources, sinks)
            flows.extend(file_flows)
            
            # Generate findings from vulnerable flows
            for flow in flows:
                if flow.is_vulnerable:
                    finding = self._create_finding(flow, parsed.file_path)
                    findings.append(finding)
            
        except Exception as e:
            logger.error(f"Error in taint analysis of {file_path}: {e}")
            errors.append(str(e))
        
        return TaintResult(
            findings=findings,
            sources=sources,
            sinks=sinks,
            flows=flows,
            errors=errors,
        )
    
    def _identify_sources(self, parsed: ParsedFile) -> List[TaintSource]:
        """Identify taint sources in the code"""
        sources = []
        language_sources = self.DEFAULT_SOURCES.get(parsed.language, [])
        
        try:
            with open(parsed.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return sources
        
        lines = content.split("\n")
        
        for line_num, line in enumerate(lines, 1):
            for source_pattern, level, source_type in language_sources:
                if source_pattern in line:
                    column = line.find(source_pattern) + 1
                    source = TaintSource(
                        name=source_pattern,
                        line=line_num,
                        column=column,
                        taint_level=level,
                        source_type=source_type,
                    )
                    sources.append(source)
        
        return sources
    
    def _identify_sinks(self, parsed: ParsedFile) -> List[TaintSink]:
        """Identify taint sinks in the code"""
        sinks = []
        language_sinks = self.DEFAULT_SINKS.get(parsed.language, [])
        
        try:
            with open(parsed.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return sinks
        
        lines = content.split("\n")
        
        for line_num, line in enumerate(lines, 1):
            for sink_pattern, sink_type, required_level in language_sinks:
                if sink_pattern in line:
                    column = line.find(sink_pattern) + 1
                    sink = TaintSink(
                        name=sink_pattern,
                        line=line_num,
                        column=column,
                        sink_type=sink_type,
                        required_taint_level=required_level,
                    )
                    sinks.append(sink)
        
        return sinks
    
    def _track_flows(
        self,
        parsed: ParsedFile,
        sources: List[TaintSource],
        sinks: List[TaintSink],
    ) -> List[TaintFlow]:
        """Track data flows from sources to sinks"""
        flows = []
        
        try:
            with open(parsed.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return flows
        
        lines = content.split("\n")
        
        for source in sources:
            for sink in sinks:
                # Simple flow detection: check if source appears before sink
                if source.line < sink.line:
                    # Check if there's a potential flow
                    flow = self._analyze_flow_between(source, sink, lines, parsed)
                    if flow:
                        flows.append(flow)
        
        return flows
    
    def _analyze_flow_between(
        self,
        source: TaintSource,
        sink: TaintSink,
        lines: List[str],
        parsed: ParsedFile,
    ) -> Optional[TaintFlow]:
        """Analyze potential flow between a source and sink"""
        # Extract variable name from source line
        source_line = lines[source.line - 1]
        variable_match = self._extract_variable(source_line, source.name)
        
        if not variable_match:
            return None
        
        variable_name = variable_match
        path = [(source.line, source.column)]
        sanitizers = []
        
        # Track variable through the code
        for line_num in range(source.line, sink.line):
            line = lines[line_num - 1]
            
            # Check if variable is used
            if variable_name in line:
                path.append((line_num, line.find(variable_name) + 1))
                
                # Check for sanitizers
                for sanitizer in self.SANITIZERS.get(parsed.language, []):
                    if sanitizer in line and variable_name in line:
                        sanitizers.append(sanitizer)
        
        path.append((sink.line, sink.column))
        
        # Determine if flow is vulnerable
        is_vulnerable = len(sanitizers) == 0
        
        # Check taint level against sink requirement
        if source.taint_level.value in ["critical", "high"]:
            is_vulnerable = is_vulnerable and True
        
        return TaintFlow(
            source=source,
            sink=sink,
            path=path,
            sanitizers=sanitizers,
            is_vulnerable=is_vulnerable,
        )
    
    def _extract_variable(self, line: str, source_pattern: str) -> Optional[str]:
        """Extract variable name from a line containing a source"""
        import re
        
        # Pattern: variable = source(...)
        match = re.search(r'(\w+)\s*=\s*' + re.escape(source_pattern), line)
        if match:
            return match.group(1)
        
        # Pattern: variable = source
        match = re.search(r'(\w+)\s*=\s*' + re.escape(source_pattern.split('.')[-1]), line)
        if match:
            return match.group(1)
        
        return None
    
    def _create_finding(self, flow: TaintFlow, file_path: str) -> TaintFinding:
        """Create a finding from a taint flow"""
        vulnerability_types = {
            "sql": ("SQL Injection", "CWE-89"),
            "command": ("Command Injection", "CWE-78"),
            "code_execution": ("Code Injection", "CWE-94"),
            "xss": ("Cross-Site Scripting", "CWE-79"),
            "deserialization": ("Insecure Deserialization", "CWE-502"),
            "file_write": ("Path Traversal", "CWE-22"),
            "open_redirect": ("Open Redirect", "CWE-601"),
        }
        
        vuln_type, cwe_id = vulnerability_types.get(
            flow.sink.sink_type,
            ("Taint Flow", "CWE-20")
        )
        
        severity_map = {
            TaintLevel.CRITICAL: "critical",
            TaintLevel.HIGH: "high",
            TaintLevel.MEDIUM: "medium",
            TaintLevel.LOW: "low",
        }
        
        message = (
            f"Potential {vuln_type} vulnerability: "
            f"Untrusted data from '{flow.source.name}' (line {flow.source.line}) "
            f"flows to '{flow.sink.name}' (line {flow.sink.line})"
        )
        
        remediation = self._get_remediation(flow.sink.sink_type)
        
        return TaintFinding(
            vulnerability_type=vuln_type,
            severity=severity_map.get(flow.source.taint_level, "medium"),
            message=message,
            source=flow.source,
            sink=flow.sink,
            file_path=file_path,
            flow_path=flow.path,
            remediation=remediation,
            cwe_id=cwe_id,
        )
    
    def _get_remediation(self, sink_type: str) -> str:
        """Get remediation advice for a sink type"""
        remediations = {
            "sql": "Use parameterized queries or prepared statements",
            "command": "Avoid shell execution; use list-based arguments",
            "code_execution": "Avoid dynamic code execution; use safer alternatives",
            "xss": "Encode output before rendering in HTML",
            "deserialization": "Use safe deserialization methods; validate input",
            "file_write": "Validate and sanitize file paths",
            "open_redirect": "Validate redirect URLs against allowlist",
        }
        return remediations.get(sink_type, "Validate and sanitize all user input")


# Global analyzer instance
_analyzer: Optional[TaintAnalyzer] = None


def get_taint_analyzer() -> TaintAnalyzer:
    """Get or create global taint analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = TaintAnalyzer()
    return _analyzer
