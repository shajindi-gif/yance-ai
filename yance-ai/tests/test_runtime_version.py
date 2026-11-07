from fastapi.testclient import TestClient

from app.main import app


def test_runtime_version_reads_actual_database_revision(monkeypatch):
    monkeypatch.setenv('APP_SOURCE_REVISION', 'synthetic-revision')
    with TestClient(app) as client:
        response = client.get('/api/v1/system/version')
    assert response.status_code == 200
    assert response.json()['database_revisions'] == ['20261106_0038']
    assert response.json()['source_revision'] == 'synthetic-revision'
