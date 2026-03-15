"""
Performance analyzer for code optimization
Detects performance bottlenecks and suggests improvements
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import structlog

from engine.ast_parser import get_parser, ParsedFile

logger = structlog.get_logger()


@dataclass
class PerformanceFinding:
    """A performance issue finding"""

    rule_id: str
    rule_name: str
    severity: str  # high, medium, low
    message: str
    file_path: str
    line_start: int
    line_end: int
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    expected_improvement: Optional[str] = None
    complexity_score: Optional[float] = None


@dataclass
class ComplexityMetrics:
    """Code complexity metrics"""

    cyclomatic_complexity: int
    cognitive_complexity: int
    lines_of_code: int
    maintainability_index: float
    halstead_volume: float
    halstead_difficulty: float


@dataclass
class PerformanceResult:
    """Result of performance analysis"""

    findings: List[PerformanceFinding] = field(default_factory=list)
    metrics: Dict[str, ComplexityMetrics] = field(default_factory=dict)
    hot_paths: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class PerformanceAnalyzer:
    """Analyze code for performance issues"""

    COMPLEXITY_THRESHOLDS = {
        "low": 10,
        "medium": 20,
        "high": 50,
    }

    def __init__(self):
        self.parser = get_parser()

    def analyze_file(self, file_path: str, content: Optional[str] = None) -> PerformanceResult:
        """Analyze a single file for performance issues"""
        findings = []
        metrics = {}
        errors = []

        try:
            # Parse the file
            parsed = self.parser.parse_file(file_path, content)

            if parsed.errors:
                errors.extend(parsed.errors)

            if parsed.language == "unknown":
                return PerformanceResult(errors=errors)

            # Analyze functions
            for func in parsed.functions:
                func_metrics = self._calculate_complexity_metrics(func, parsed)
                metrics[func.name] = func_metrics

                # Check complexity thresholds
                if func_metrics.cyclomatic_complexity > self.COMPLEXITY_THRESHOLDS["high"]:
                    finding = PerformanceFinding(
                        rule_id="PERF-C001",
                        rule_name="Very High Cyclomatic Complexity",
                        severity="high",
                        message=f"Function '{func.name}' has very high cyclomatic complexity ({func_metrics.cyclomatic_complexity})",
                        file_path=parsed.file_path,
                        line_start=func.start_line,
                        line_end=func.end_line,
                        suggestion="Refactor the function into smaller, more manageable functions",
                        expected_improvement="Improved testability and maintainability",
                        complexity_score=func_metrics.cyclomatic_complexity,
                    )
                    findings.append(finding)
                elif func_metrics.cyclomatic_complexity > self.COMPLEXITY_THRESHOLDS["medium"]:
                    finding = PerformanceFinding(
                        rule_id="PERF-C002",
                        rule_name="High Cyclomatic Complexity",
                        severity="medium",
                        message=f"Function '{func.name}' has high cyclomatic complexity ({func_metrics.cyclomatic_complexity})",
                        file_path=parsed.file_path,
                        line_start=func.start_line,
                        line_end=func.end_line,
                        suggestion="Consider simplifying the function logic",
                        complexity_score=func_metrics.cyclomatic_complexity,
                    )
                    findings.append(finding)

                # Check function length
                func_lines = func.end_line - func.start_line
                if func_lines > 100:
                    finding = PerformanceFinding(
                        rule_id="PERF-S001",
                        rule_name="Very Long Function",
                        severity="medium",
                        message=f"Function '{func.name}' is very long ({func_lines} lines)",
                        file_path=parsed.file_path,
                        line_start=func.start_line,
                        line_end=func.end_line,
                        suggestion="Break the function into smaller functions",
                        expected_improvement="Better readability and maintainability",
                    )
                    findings.append(finding)

            # Language-specific analysis
            if parsed.language == "python":
                python_findings = self._analyze_python_performance(parsed)
                findings.extend(python_findings)
            elif parsed.language in ["javascript", "typescript"]:
                js_findings = self._analyze_javascript_performance(parsed)
                findings.extend(js_findings)

            # Pattern-based analysis
            pattern_findings = self._analyze_patterns(parsed)
            findings.extend(pattern_findings)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            errors.append(str(e))

        return PerformanceResult(
            findings=findings,
            metrics=metrics,
            errors=errors,
        )

    def _calculate_complexity_metrics(self, func, parsed: ParsedFile) -> ComplexityMetrics:
        """Calculate complexity metrics for a function"""
        # Use the complexity from the parser
        cyclomatic = func.complexity

        # Estimate cognitive complexity (simplified)
        cognitive = cyclomatic  # In real implementation, this would be more sophisticated

        # Lines of code
        loc = func.end_line - func.start_line

        # Maintainability Index (simplified formula)
        # MI = 171 - 5.2 * ln(Halstead Volume) - 0.23 * (Cyclomatic Complexity) - 16.2 * ln(Lines of Code)
        import math

        halstead_volume = loc * 10  # Simplified
        if halstead_volume > 0 and loc > 0:
            mi = max(
                0, 171 - 5.2 * math.log(halstead_volume) - 0.23 * cyclomatic - 16.2 * math.log(loc)
            )
        else:
            mi = 100

        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            lines_of_code=loc,
            maintainability_index=round(mi, 2),
            halstead_volume=halstead_volume,
            halstead_difficulty=cyclomatic * 0.5,
        )

    def _analyze_python_performance(self, parsed: ParsedFile) -> List[PerformanceFinding]:
        """Python-specific performance analysis"""
        findings = []

        try:
            with open(parsed.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return findings

        lines = content.split("\n")

        # Check for inefficient patterns
        patterns = [
            {
                "id": "PERF-P001",
                "name": "Inefficient List Concatenation",
                "pattern": r"\+\s*\[",
                "message": "Using '+' to concatenate lists is inefficient (O(n^2))",
                "suggestion": "Use list.append() or list.extend() instead",
                "severity": "medium",
            },
            {
                "id": "PERF-P002",
                "name": "String Concatenation in Loop",
                "pattern": r"for.*:\s*\n.*\+\s*=",
                "message": "String concatenation in a loop is inefficient",
                "suggestion": "Use str.join() or io.StringIO instead",
                "severity": "medium",
            },
            {
                "id": "PERF-P003",
                "name": "Inefficient Dictionary Lookup",
                "pattern": r"\.keys\(\)\s*.*in",
                "message": "Using .keys() for membership testing is inefficient",
                "suggestion": "Use 'key in dict' instead of 'key in dict.keys()'",
                "severity": "low",
            },
            {
                "id": "PERF-P004",
                "name": "List Comprehension Alternative",
                "pattern": r"for\s+\w+\s+in\s+\w+:\s*\n\s*\w+\.append\(",
                "message": "Consider using list comprehension for better performance",
                "suggestion": "Replace loop with list comprehension",
                "severity": "low",
            },
            {
                "id": "PERF-P005",
                "name": "Repeated Attribute Access",
                "pattern": r"(\w+\.\w+).*\n.*\1.*\n.*\1",
                "message": "Repeated attribute access in loop can be slow",
                "suggestion": "Cache the attribute in a local variable",
                "severity": "low",
            },
        ]

        for pattern_def in patterns:
            try:
                pattern = re.compile(pattern_def["pattern"], re.MULTILINE)
                for line_num, line in enumerate(lines, 1):
                    if pattern.search(line):
                        finding = PerformanceFinding(
                            rule_id=pattern_def["id"],
                            rule_name=pattern_def["name"],
                            severity=pattern_def["severity"],
                            message=pattern_def["message"],
                            file_path=parsed.file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            suggestion=pattern_def["suggestion"],
                        )
                        findings.append(finding)
            except re.error:
                continue

        # Check for import patterns
        import_lines = []
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                import_lines.append((i + 1, line))

        # Check for imports inside functions (lazy loading is good, but can be slow)
        for func in parsed.functions:
            for line_num, line in import_lines:
                if func.start_line <= line_num <= func.end_line:
                    finding = PerformanceFinding(
                        rule_id="PERF-P006",
                        rule_name="Import Inside Function",
                        severity="low",
                        message=f"Import statement inside function '{func.name}'",
                        file_path=parsed.file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip(),
                        suggestion="Consider moving import to module level unless lazy loading is intentional",
                    )
                    findings.append(finding)

        return findings

    def _analyze_javascript_performance(self, parsed: ParsedFile) -> List[PerformanceFinding]:
        """JavaScript-specific performance analysis"""
        findings = []

        try:
            with open(parsed.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return findings

        lines = content.split("\n")

        # Check for inefficient patterns
        patterns = [
            {
                "id": "PERF-J001",
                "name": "Inefficient DOM Access",
                "pattern": r"document\.getElementById|document\.querySelector",
                "message": "Repeated DOM access can be slow",
                "suggestion": "Cache DOM references in variables",
                "severity": "medium",
            },
            {
                "id": "PERF-J002",
                "name": "console.log in Production",
                "pattern": r"console\.(log|debug|info)\(",
                "message": "Console statements can slow down performance",
                "suggestion": "Remove console statements in production code",
                "severity": "low",
            },
            {
                "id": "PERF-J003",
                "name": "Inefficient Loop",
                "pattern": r"for\s*\(\s*var\s+i\s*=\s*0;\s*i\s*<\s*\w+\.length",
                "message": "Accessing .length on each iteration is inefficient",
                "suggestion": "Cache the length: for (var i = 0, len = arr.length; i < len; i++)",
                "severity": "low",
            },
        ]

        for pattern_def in patterns:
            try:
                pattern = re.compile(pattern_def["pattern"])
                for line_num, line in enumerate(lines, 1):
                    if pattern.search(line):
                        finding = PerformanceFinding(
                            rule_id=pattern_def["id"],
                            rule_name=pattern_def["name"],
                            severity=pattern_def["severity"],
                            message=pattern_def["message"],
                            file_path=parsed.file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            suggestion=pattern_def["suggestion"],
                        )
                        findings.append(finding)
            except re.error:
                continue

        return findings

    def _analyze_patterns(self, parsed: ParsedFile) -> List[PerformanceFinding]:
        """Analyze code for general performance anti-patterns"""
        findings = []

        # Check for deeply nested blocks
        for func in parsed.functions:
            nesting_level = self._calculate_nesting_level(func, parsed)
            if nesting_level > 4:
                finding = PerformanceFinding(
                    rule_id="PERF-N001",
                    rule_name="Deep Nesting",
                    severity="medium",
                    message=f"Function '{func.name}' has deep nesting (level {nesting_level})",
                    file_path=parsed.file_path,
                    line_start=func.start_line,
                    line_end=func.end_line,
                    suggestion="Consider extracting nested logic into separate functions",
                )
                findings.append(finding)

        return findings

    def _calculate_nesting_level(self, func, parsed: ParsedFile) -> int:
        """Calculate maximum nesting level of a function"""
        # Simplified implementation
        # In a real implementation, this would analyze the AST
        return min(func.complexity // 3, 10)  # Rough estimate

    def get_hot_paths(self, file_path: str) -> List[Dict]:
        """Identify potential hot paths in the code"""
        hot_paths = []

        result = self.analyze_file(file_path)

        # Sort functions by complexity
        sorted_funcs = sorted(
            result.metrics.items(),
            key=lambda x: x[1].cyclomatic_complexity,
            reverse=True,
        )

        for func_name, metrics in sorted_funcs[:5]:
            hot_paths.append(
                {
                    "function": func_name,
                    "complexity": metrics.cyclomatic_complexity,
                    "lines": metrics.lines_of_code,
                    "maintainability": metrics.maintainability_index,
                }
            )

        return hot_paths


# Global analyzer instance
_analyzer: Optional[PerformanceAnalyzer] = None


def get_analyzer() -> PerformanceAnalyzer:
    """Get or create global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = PerformanceAnalyzer()
    return _analyzer
