"""Integration tests for the API service."""

from fastapi.testclient import TestClient

from services.api import main as api_main
from services.api.middleware.auth import create_access_token


def test_repository_create_and_analyze(monkeypatch):
    """Ensure we can create a repository and queue analysis."""

    # Avoid requiring real DB/Redis services during fast unit tests.
    async def _noop():
        return None

    monkeypatch.setattr(api_main, "init_db", _noop)
    monkeypatch.setattr(api_main, "close_db", _noop)

    client = TestClient(api_main.app)

    token = create_access_token(user_id="test", email="test@example.com", roles=["user"])
    headers = {"Authorization": f"Bearer {token}"}

    # Create a repository
    resp = client.post(
        "/api/v1/repositories",
        headers=headers,
        json={"url": "https://github.com/example/repo", "branch": "main"},
    )
    assert resp.status_code == 201
    repo_id = resp.json()["id"]

    # Trigger analysis
    resp = client.post(
        f"/api/v1/repositories/{repo_id}/analyze",
        headers=headers,
        json={"analysis_types": ["security", "performance"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
