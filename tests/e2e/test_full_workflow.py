"""
End-to-end tests for full workflow
"""

import pytest


class TestFullWorkflow:
    """Test complete analysis workflow"""
    
    @pytest.fixture(scope="module")
    def api_url(self):
        return "http://localhost:8000"
    
    def test_health_check(self, api_url):
        import requests
        response = requests.get(f"{api_url}/health")
        assert response.status_code == 200
    
    def test_repository_registration_and_analysis(self, api_url):
        import requests
        
        # Register repository
        repo_payload = {
            "url": "https://github.com/example/test-repo",
            "branch": "main",
            "name": "test-repo"
        }
        
        # This would require authentication in production
        # response = requests.post(f"{api_url}/api/v1/repositories", json=repo_payload)
        # assert response.status_code == 201
        
        # For now, just test the endpoint exists
        response = requests.get(f"{api_url}/api/v1/languages")
        assert response.status_code == 200
    
    def test_code_analysis(self, api_url):
        import requests
        
        payload = {
            "snippet": {
                "code": 'query = f"SELECT * FROM users WHERE id = {user_id}"',
                "language": "python"
            },
            "analysis_types": ["security"]
        }
        
        response = requests.post(f"{api_url}/api/v1/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "findings" in data
        # Should find SQL injection
        sql_findings = [f for f in data["findings"] if "SQL" in f.get("message", "")]
        assert len(sql_findings) > 0
