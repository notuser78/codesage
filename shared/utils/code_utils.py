"""
Code utility functions
"""

import hashlib
import re
from pathlib import Path
from typing import List, Optional, Tuple


# Language detection
LANGUAGE_EXTENSIONS = {
    "python": [".py", ".pyw", ".pyi"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx", ".mts", ".cts"],
    "java": [".java"],
    "go": [".go"],
    "rust": [".rs"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hh"],
    "c": [".c", ".h"],
    "csharp": [".cs"],
    "php": [".php", ".phtml"],
    "ruby": [".rb", ".erb"],
    "swift": [".swift"],
    "kotlin": [".kt", ".kts"],
    "scala": [".scala"],
    "r": [".r", ".R"],
    "matlab": [".m"],
    "sql": [".sql"],
    "shell": [".sh", ".bash", ".zsh"],
    "powershell": [".ps1"],
    "yaml": [".yaml", ".yml"],
    "json": [".json"],
    "xml": [".xml"],
    "html": [".html", ".htm"],
    "css": [".css", ".scss", ".sass", ".less"],
    "markdown": [".md", ".markdown"],
    "dockerfile": ["Dockerfile"],
    "makefile": ["Makefile", ".mk"],
}


def detect_language(file_path: str) -> Optional[str]:
    """Detect programming language from file path"""
    path = Path(file_path)
    ext = path.suffix.lower()
    name = path.name
    
    # Check by extension
    for lang, extensions in LANGUAGE_EXTENSIONS.items():
        if ext in extensions:
            return lang
        if name in extensions:
            return lang
    
    return None


def get_file_extension(language: str) -> Optional[str]:
    """Get primary file extension for a language"""
    extensions = LANGUAGE_EXTENSIONS.get(language)
    return extensions[0] if extensions else None


def calculate_hash(content: str) -> str:
    """Calculate MD5 hash of content"""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def normalize_code(content: str, language: str) -> str:
    """Normalize code by removing comments and extra whitespace"""
    # Remove single-line comments
    if language in ["python", "yaml", "shell", "ruby", "perl"]:
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
    elif language in ["javascript", "typescript", "java", "cpp", "c", "go", "rust", "swift"]:
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
    content = re.sub(r"'''.*?'''", '', content, flags=re.DOTALL)
    
    # Normalize whitespace
    lines = content.split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    
    return '\n'.join(lines)


def extract_imports(content: str, language: str) -> List[str]:
    """Extract import statements from code"""
    imports = []
    
    if language == "python":
        # Match 'import X' and 'from X import Y'
        import_pattern = r'^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            module = match.group(1) or ""
            names = match.group(2)
            imports.append(f"{module}.{names}" if module else names)
    
    elif language in ["javascript", "typescript"]:
        # Match ES6 imports and require
        import_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))
        for match in re.finditer(require_pattern, content):
            imports.append(match.group(1))
    
    elif language == "java":
        import_pattern = r'^\s*import\s+([^;]+);'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            imports.append(match.group(1))
    
    elif language == "go":
        import_pattern = r'^\s*import\s+["\']([^"\']+)["\']'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            imports.append(match.group(1))
    
    return imports


def count_lines(content: str) -> Tuple[int, int, int]:
    """Count total, code, and comment lines"""
    lines = content.split('\n')
    total = len(lines)
    
    code_lines = 0
    comment_lines = 0
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            continue
        
        if in_multiline_comment:
            comment_lines += 1
            if '*/' in stripped or '"""' in stripped or "'''" in stripped:
                in_multiline_comment = False
        elif stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('*'):
            comment_lines += 1
        elif stripped.startswith('/*') or stripped.startswith('"""') or stripped.startswith("'''"):
            comment_lines += 1
            in_multiline_comment = True
        else:
            code_lines += 1
    
    return total, code_lines, comment_lines


def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\x00' in chunk
    except Exception:
        return True


def get_mime_type(file_path: str) -> str:
    """Get MIME type for a file"""
    import mimetypes
    mime, _ = mimetypes.guess_type(file_path)
    return mime or "application/octet-stream"


def truncate_code(content: str, max_lines: int = 50, max_chars: int = 5000) -> str:
    """Truncate code to reasonable size for analysis"""
    lines = content.split('\n')
    
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append('... [truncated]')
    
    result = '\n'.join(lines)
    
    if len(result) > max_chars:
        result = result[:max_chars] + '\n... [truncated]'
    
    return result


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage"""
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    return sanitized[:255]  # Limit length


def parse_git_url(url: str) -> dict:
    """Parse a Git URL into components"""
    # HTTPS: https://github.com/user/repo.git
    # SSH: git@github.com:user/repo.git
    
    result = {
        "provider": None,
        "owner": None,
        "repo": None,
        "protocol": None,
    }
    
    if url.startswith('https://') or url.startswith('http://'):
        result["protocol"] = "https"
        parts = url.replace('https://', '').replace('http://', '').split('/')
        if len(parts) >= 3:
            result["provider"] = parts[0]
            result["owner"] = parts[1]
            result["repo"] = parts[2].replace('.git', '')
    
    elif url.startswith('git@'):
        result["protocol"] = "ssh"
        parts = url.replace('git@', '').split(':')
        if len(parts) >= 2:
            result["provider"] = parts[0]
            repo_parts = parts[1].split('/')
            if len(repo_parts) >= 2:
                result["owner"] = repo_parts[0]
                result["repo"] = repo_parts[1].replace('.git', '')
    
    return result
