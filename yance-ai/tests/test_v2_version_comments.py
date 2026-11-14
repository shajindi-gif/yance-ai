"""Synthetic version-comment authorization and historical binding regression."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_funding_os import _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    Application,
    ApplicationActivity,
    ApplicationArtifact,
    Membership,
    User,
)


def test_version_comments_are_scoped_immutable_and_audited():
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        other_headers, _ = _register(client, uuid.uuid4().hex)
        company = client.get("/api/v1/companies", headers=headers).json()[0]
        with SessionLocal() as db:
            application = Application(
                tenant_id=uuid.UUID(me["tenant_id"]),
                company_id=uuid.UUID(company["id"]),
                title="合成审阅",
            )
            sibling = Application(
                tenant_id=application.tenant_id,
                company_id=application.company_id,
                title="另一个项目",
            )
            db.add_all([application, sibling])
            db.flush()
            drafts = []
            for project, version in [(application, 1), (application, 2), (sibling, 1)]:
                draft = ApplicationArtifact(
                    tenant_id=application.tenant_id,
                    application_id=project.id,
                    title="合成稿",
                    version=version,
                    content_json={},
                    source_snapshot_json={},
                    checksum_sha256="synthetic",
                )
                db.add(draft)
                drafts.append(draft)
            db.commit()
            app_id = str(application.id)
            old_id = str(drafts[0].id)
            wrong_id = str(drafts[2].id)
        url = f"/api/v1/applications/{app_id}/comments"
        result = client.post(
            url, headers=headers, json={"body": "核实旧版证据", "artifact_id": old_id}
        )
        assert result.status_code == 201, result.text
        assert result.json()["artifact_id"] == old_id
        comment_id = result.json()["id"]
        assert (
            client.post(
                url, headers=headers, json={"body": "跨项目", "artifact_id": wrong_id}
            ).status_code
            == 404
        )
        assert (
            client.post(
                url, headers=other_headers, json={"body": "跨租户", "artifact_id": old_id}
            ).status_code
            == 404
        )
        assert (
            client.post(
                url, headers=headers, json={"body": "  ", "artifact_id": old_id}
            ).status_code
            == 422
        )
        assert (
            client.post(url, headers=headers, json={"body": "项目整体"}).json()["artifact_id"]
            is None
        )
        detail = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert detail.status_code == 200, detail.text
        assert (
            next(c for c in detail.json()["comments"] if c["id"] == comment_id)["artifact_id"]
            == old_id
        )
        with SessionLocal() as db:
            event = db.scalar(
                select(ApplicationActivity)
                .where(
                    ApplicationActivity.application_id == uuid.UUID(app_id),
                    ApplicationActivity.action == "comment_added",
                )
                .order_by(ApplicationActivity.occurred_at)
            )
            assert event.metadata_json["comment_id"] == comment_id
            assert event.metadata_json["artifact_id"] == old_id
            user = db.get(User, uuid.UUID(me["id"]))
            user.role = "viewer"
            membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
            membership.role = "viewer"
            db.commit()
        assert (
            client.post(
                url, headers=headers, json={"body": "只读不可评论", "artifact_id": old_id}
            ).status_code
            == 403
        )
