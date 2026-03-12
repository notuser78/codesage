"""
Unit tests for security scanner
"""

import pytest

pytest.importorskip("tree_sitter")

from engine.security_scanner import SecurityScanner, get_scanner


class TestSecurityScanner:
    """Test security scanner functionality"""
    
    @pytest.fixture
    def scanner(self):
        return get_scanner()
    
    def test_scan_python_sql_injection(self, scanner):
        code = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()
"""
        result = scanner._scan_with_rules("test.py", code, "python")
        
        # Should find SQL injection vulnerability
        sql_injection = [f for f in result if "SQL" in f.message]
        assert len(sql_injection) > 0
    
    def test_scan_python_hardcoded_secret(self, scanner):
        code = """
API_KEY = "sk-1234567890abcdef"
password = "super_secret_password"
"""
        result = scanner._scan_with_rules("test.py", code, "python")
        
        # Should find hardcoded secrets
        secrets = [f for f in result if "secret" in f.message.lower()]
        assert len(secrets) > 0
    
    def test_scan_python_insecure_deserialization(self, scanner):
        code = """
import pickle

def load_data(data):
    return pickle.loads(data)
"""
        result = scanner._scan_with_rules("test.py", code, "python")
        
        # Should find insecure deserialization
        deser = [f for f in result if "deserialization" in f.message.lower()]
        assert len(deser) > 0
    
    def test_scan_javascript_xss(self, scanner):
        code = """
function displayUserInput(input) {
    document.innerHTML = input;
}
"""
        result = scanner._scan_with_rules("test.js", code, "javascript")
        
        # Should find XSS vulnerability
        xss = [f for f in result if "XSS" in f.message]
        assert len(xss) > 0
    
    def test_cwe_to_owasp_mapping(self, scanner):
        assert scanner.CWE_TO_OWASP.get("CWE-89") == "A03"  # SQL Injection
        assert scanner.CWE_TO_OWASP.get("CWE-79") == "A03"  # XSS
        assert scanner.CWE_TO_OWASP.get("CWE-78") == "A03"  # Command Injection
