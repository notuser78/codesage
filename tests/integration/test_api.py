"""
Integration tests for API Gateway
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestAPI:
    """Test API endpoints"""
    
    @pytest_asyncio.fixture
    async def client(self):
        from services.api import main as api_main
        from services.api.middleware.auth import create_access_token

        token = create_access_token("test-user", "test@example.com")
        async with AsyncClient(
            app=api_main.app,
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_analyze_code(self, client):
        payload = {
            "snippet": {
                "code": "def test(): pass",
                "language": "python"
            },
            "analysis_types": ["security"]
        }
        response = await client.post("/api/v1/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "status" in data
    
    @pytest.mark.asyncio
    async def test_list_languages(self, client):
        response = await client.get("/api/v1/languages")
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert len(data["languages"]) > 0
    
    @pytest.mark.asyncio
    async def test_list_rules(self, client):
        response = await client.get("/api/v1/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
