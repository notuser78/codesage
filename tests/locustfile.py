"""
Locust load testing configuration
"""

from locust import HttpUser, between, task


class CodeSageUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 5)
    
    def on_start(self):
        """Called when a user starts"""
        pass
    
    @task(3)
    def health_check(self):
        """Test health endpoint"""
        self.client.get("/health")
    
    @task(2)
    def list_languages(self):
        """Test languages endpoint"""
        self.client.get("/api/v1/languages")
    
    @task(2)
    def list_rules(self):
        """Test rules endpoint"""
        self.client.get("/api/v1/rules")
    
    @task(1)
    def analyze_code(self):
        """Test analysis endpoint"""
        payload = {
            "snippet": {
                "code": "def test(): pass",
                "language": "python"
            },
            "analysis_types": ["security"]
        }
        self.client.post("/api/v1/analyze", json=payload)
