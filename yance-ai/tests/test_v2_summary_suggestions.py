"""Synthetic persisted suggestion decisions, never provider calls."""

import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_funding_os import _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Application, ApplicationArtifact, UsageRecord
from app.services.applications.workspace import create_artifact


def test_accept_is_atomic_idempotent_and_stale_suggestions_are_blocked(monkeypatch):
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        other, _ = _register(client, uuid.uuid4().hex)
        company = client.get("/api/v1/companies", headers=headers).json()[0]
        with SessionLocal() as db:
            project = Application(
                tenant_id=uuid.UUID(me["tenant_id"]),
                company_id=uuid.UUID(company["id"]),
                title="合成建议项目",
            )
            db.add(project)
            db.flush()
            source = create_artifact(db, project, user_id=uuid.UUID(me["id"]))
            db.commit()
            project_id = str(project.id)
            source_id = str(source.id)
        url = f"/api/v1/applications/{project_id}/comments"

        def propose():
            response = client.post(
                url,
                headers=headers,
                json={
                    "body": "人工建议",
                    "artifact_id": source_id,
                    "proposed_summary": "经人工修改的合成摘要",
                },
            )
            assert response.status_code == 201, response.text
            return response.json()["id"]

        first, stale, rejected = propose(), propose(), propose()
        assert (
            client.post(
                url, headers=headers, json={"body": "缺版本", "proposed_summary": "建议摘要"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"{url}/{first}/decision", headers=other, json={"decision": "accept"}
            ).status_code
            == 404
        )

        # This fixture has no policy. Verify the real source gate first, then
        # isolate transactional acceptance with an explicitly controlled gate.
        assert (
            client.post(
                f"{url}/{first}/decision", headers=headers, json={"decision": "accept"}
            ).status_code
            == 409
        )
        monkeypatch.setattr(
            "app.api.routes.workflow.artifact_source_state", lambda *_: {"current": True}
        )

        def accept(_):
            with TestClient(app) as worker:
                result = worker.post(
                    f"{url}/{first}/decision", headers=headers, json={"decision": "accept"}
                )
                assert result.status_code == 200, result.text
                return result.json()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(accept, range(2)))
        assert outcomes[0] == outcomes[1]
        assert outcomes[0]["artifact_id"] != source_id
        assert (
            client.post(
                f"{url}/{stale}/decision", headers=headers, json={"decision": "accept"}
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"{url}/{first}/decision", headers=headers, json={"decision": "reject"}
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"{url}/{rejected}/decision", headers=headers, json={"decision": "reject"}
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            rows = db.scalars(
                select(ApplicationArtifact).where(
                    ApplicationArtifact.application_id == uuid.UUID(project_id)
                )
            ).all()
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(UsageRecord)
                    .where(
                        UsageRecord.tenant_id == uuid.UUID(me["tenant_id"]),
                        UsageRecord.meter_key == "generated_documents",
                    )
                )
                == 0
            )
            assert len(rows) == 2
            latest = max(rows, key=lambda item: item.version)
            assert latest.status == "draft"
            assert latest.content_json["executive_summary"] == "经人工修改的合成摘要"
