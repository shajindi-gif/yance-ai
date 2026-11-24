"""Regression for acceptance ACC-16: missing OSS configuration is a 503, not a 500."""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.oss import get_oss_storage

pytestmark = pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")


def test_document_routes_return_503_when_object_storage_is_not_configured(monkeypatch):
    for name in ("oss_endpoint", "oss_bucket", "oss_access_key_id", "oss_access_key_secret"):
        monkeypatch.setattr(f"app.services.oss.settings.{name}", "")
    get_oss_storage.cache_clear()
    client = TestClient(app, raise_server_exceptions=False)
    registered = client.post("/api/v1/auth/register", json={
        "company_name": "合成存储企业", "owner_email": f"oss-{uuid.uuid4().hex}@example.com",
        "owner_name": "合成用户", "owner_password": "synthetic-password-123456", "agreed_terms_version": "test-terms",
    })
    assert registered.status_code == 201, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    response = client.post(f"/api/v1/documents/{uuid.uuid4()}/complete", headers=headers, json={})
    assert response.status_code == 503
    assert "storage" in response.json()["detail"].lower()
