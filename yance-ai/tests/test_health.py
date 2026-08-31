from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_required_api_paths_are_registered():
    paths = set(app.openapi()["paths"])
    required = {
        "/health",
        "/health/ready",
        "/api/v1/auth/login",
        "/api/v1/companies",
        "/api/v1/documents/presign-upload",
        "/api/v1/policies",
        "/api/v1/policy-rules",
        "/api/v1/opportunities",
        "/api/v1/applications",
    }
    assert required <= paths
