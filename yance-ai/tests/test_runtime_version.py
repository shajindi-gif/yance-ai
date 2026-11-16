from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient

from app.main import app


def test_runtime_version_reads_actual_database_revision(monkeypatch):
    monkeypatch.setenv('APP_SOURCE_REVISION', 'synthetic-revision')
    with TestClient(app) as client:
        response = client.get('/api/v1/system/version')
    assert response.status_code == 200
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    assert sorted(response.json()['database_revisions']) == sorted(ScriptDirectory.from_config(config).get_heads())
    assert response.json()['source_revision'] == 'synthetic-revision'
