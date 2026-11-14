"""Read-only API and schema checks against isolated restored data.

APP_ENV=test, localhost and explicitly named recovery DB only. Never seed users
or run workers on this customer snapshot; synthetic tests use a separate DB.
"""
import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.api.deps import Principal, get_principal
from app.models.models import User, UserRole

url = make_url(settings.database_url)
assert settings.app_env == 'test' and url.host == '127.0.0.1'
assert url.database == 'yance_release_test'
assert not settings.email_enabled and settings.llm_default_provider == 'mock'
with SessionLocal() as db:
    assert db.scalar(text('SELECT version_num FROM alembic_version')) == '20261027_0033'
with TestClient(app) as client:
    for path in ['/health', '/health/ready', '/api/v1/products', '/api/v1/auth/config']:
        assert client.get(path).status_code == 200, path
    config = client.get('/api/v1/auth/config').json()
    assert config['feedback_revision'] == 1 and config['application_workspace_revision'] == 2
    for path in ['/api/v1/auth/me', '/api/v1/feedback', '/api/v1/companies', '/api/v1/orders']:
        assert client.get(path).status_code == 401, path
    # Transient principals, no inserts and no real customer identity. Exercise
    # tenant filters on the actual legacy NULL-tenant rows in the restored copy.
    try:
        for _ in range(2):
            tenant = uuid.uuid4()
            principal = Principal(user=User(id=uuid.uuid4(),tenant_id=tenant),tenant_id=tenant,role=UserRole.owner)
            app.dependency_overrides[get_principal] = lambda: principal
            response = client.get('/api/v1/policy-rules')
            assert response.status_code == 200 and response.json() == []
            response = client.get('/api/v1/analytics/stats')
            assert response.status_code == 200 and response.json()['total_events'] == 0
    finally:
        app.dependency_overrides.clear()
print(json.dumps({'passed': True, 'schema': '20261027_0033', 'public_api_checks': 4, 'unauthenticated_denials': 4, 'legacy_unowned_rows_excluded_for_two_transient_tenants':True,'authentication_mocked_only_in_isolated_process':True,'customer_business_writes': False, 'external_network': False}))
