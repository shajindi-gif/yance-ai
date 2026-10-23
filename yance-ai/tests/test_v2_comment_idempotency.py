"""Real database/API duplicate submission checks on synthetic evidence projects."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_v2_suggestion_evidence import _project

from app.core.db import SessionLocal
from app.main import app
from app.models.models import ApplicationActivity, ApplicationComment


@pytest.mark.parametrize("suggestion", [False, True])
def test_duplicate_creation_is_serialized_and_payload_conflicts_fail(suggestion):
    with TestClient(app) as client:
        headers, _, app_id, artifact, _, _ = _project(client)
        url = f"/api/v1/applications/{app_id}/comments"
        payload = {
            "body": "重复提交合成评论",
            "client_request_id": str(uuid.uuid4()),
            "artifact_id": artifact["id"],
        }
        if suggestion:
            payload["proposed_summary"] = "合成修改建议"

        def submit(_):
            with TestClient(app) as caller:
                result = caller.post(url, headers=headers, json=payload)
                assert result.status_code == 201, result.text
                return result.json()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(submit, range(2)))
        assert responses[0] == responses[1]
        assert client.post(url, headers=headers, json=payload).json() == responses[0]
        for changes in [
            {"body": "不同内容"},
            {"artifact_id": None},
            {"proposed_summary": "另一摘要"},
        ]:
            assert client.post(url, headers=headers, json={**payload, **changes}).status_code == 409
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ApplicationComment)
                    .where(ApplicationComment.application_id == uuid.UUID(app_id))
                )
                == 2
            )
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ApplicationActivity)
                    .where(
                        ApplicationActivity.application_id == uuid.UUID(app_id),
                        ApplicationActivity.action == "comment_added",
                    )
                )
                == 2
            )
        legacy = {"body": "旧客户端无标识"}
        first = client.post(url, headers=headers, json=legacy)
        second = client.post(url, headers=headers, json=legacy)
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] != second.json()["id"]
