import os
from pathlib import Path

os.environ["OPENMANUS_ENV"] = "test"
os.environ["OPENMANUS_JWT_SECRET"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_openmanus_platform.db"

from fastapi.testclient import TestClient

from platform_core.api import app


TEST_DB = Path("test_openmanus_platform.db")


def test_platform_auth_and_project_flow():
    if TEST_DB.exists():
        TEST_DB.unlink()

    with TestClient(app) as client:
        response = client.post(
            "/v1/auth/register",
            json={"email": "owner@example.com", "password": "strong-password-123"},
        )
        assert response.status_code == 201
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/v1/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "owner@example.com"

        response = client.post(
            "/v1/projects",
            headers=headers,
            json={"name": "First project", "description": "platform smoke test"},
        )
        assert response.status_code == 201
        project_id = response.json()["id"]

        response = client.get("/v1/projects", headers=headers)
        assert response.status_code == 200
        assert any(project["id"] == project_id for project in response.json())

    if TEST_DB.exists():
        TEST_DB.unlink()
