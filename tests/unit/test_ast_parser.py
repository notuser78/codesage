"""
Unit tests for AST parser
"""

import pytest

pytest.importorskip("tree_sitter")

from engine.ast_parser import ASTParser, get_parser


class TestASTParser:
    """Test AST parser functionality"""
    
    @pytest.fixture
    def parser(self):
        return get_parser()
    
    def test_detect_language_python(self, parser):
        assert parser.detect_language("test.py") == "python"
        assert parser.detect_language("/path/to/file.py") == "python"
    
    def test_detect_language_javascript(self, parser):
        assert parser.detect_language("test.js") == "javascript"
        assert parser.detect_language("test.jsx") == "javascript"
    
    def test_detect_language_unknown(self, parser):
        assert parser.detect_language("test.xyz") is None
    
    def test_parse_python_function(self, parser):
        code = """
def hello_world(name: str) -> str:
    return f"Hello, {name}!"
"""
        result = parser.parse_string(code, "python")
        
        assert result.language == "python"
        assert len(result.functions) == 1
        assert result.functions[0].name == "hello_world"
        assert result.functions[0].return_type == "str"
    
    def test_parse_python_class(self, parser):
        code = """
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        return a - b
"""
        result = parser.parse_string(code, "python")
        
        assert len(result.classes) == 1
        assert result.classes[0].name == "Calculator"
        assert len(result.classes[0].methods) == 2
    
    def test_parse_javascript_function(self, parser):
        code = """
function greet(name) {
    return `Hello, ${name}!`;
}

const add = (a, b) => a + b;
"""
        result = parser.parse_string(code, "javascript")
        
        assert result.language == "javascript"
        assert len(result.functions) >= 1
    
    def test_calculate_complexity(self, parser):
        code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            return "large"
        else:
            return "small"
    elif x < 0:
        return "negative"
    else:
        return "zero"
"""
        result = parser.parse_string(code, "python")
        
        assert len(result.functions) == 1
        # Complexity should be > 1 due to if/elif/else
        assert result.functions[0].complexity > 1
