import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from test_agent_harness import _queued_run
from test_audit_auth_lifecycle import _account

from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.services.agents.harness import AgentHarness

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")]


def test_cancelled_run_never_calls_executor(monkeypatch):
    async def forbidden(*args):
        raise AssertionError("cancelled task executed")
    monkeypatch.setattr("app.services.agents.harness.execute_policy_scan", forbidden)
    with SessionLocal() as db:
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        run.status = "cancelled"
        db.commit()
        asyncio.run(AgentHarness().execute(db, run.id))
        db.refresh(run)
        assert run.status == "cancelled"
        assert run.retry_count == 0


def test_worker_does_not_trust_payload_tenant_or_user(monkeypatch):
    async def forbidden(*args):
        raise AssertionError("tool must not execute")
    monkeypatch.setattr("app.services.agents.policy_scan.match_policies_for_company", forbidden)
    with SessionLocal() as db:
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        run.input_json = {**run.input_json, "tenant_id": str(uuid.uuid4())}
        db.commit()
        asyncio.run(AgentHarness().execute(db, run.id))
        db.refresh(run)
        assert run.status == "failed"
        assert run.error_code == "verification_failed"
        assert run.retry_count == 0


def test_run_timeout_is_bounded_and_retryable(monkeypatch):
    async def slow(*args):
        await asyncio.sleep(10)
    monkeypatch.setattr("app.services.agents.harness.execute_policy_scan", slow)
    monkeypatch.setattr(settings, "agent_run_timeout_seconds", 0.01)
    with SessionLocal() as db:
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        asyncio.run(AgentHarness().execute(db, run.id))
        db.refresh(run)
        assert run.status == "queued"
        assert run.retry_count == 1
        run.status = "cancelled"  # leave no runnable fixture in shared suite
        db.commit()


def test_cancel_api_is_tenant_scoped_and_idempotent():
    client = TestClient(app)
    _, foreign = _account(client)
    with SessionLocal() as db:
        from app.core.security import create_access_token
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        db.commit()
        token = create_access_token(user_id=run.user_id, tenant_id=run.tenant_id, role="owner")
        run_id = run.id
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(f"/api/v1/agent-runs/{run_id}/cancel", headers=foreign).status_code == 404
    assert client.post(f"/api/v1/agent-runs/{run_id}/cancel", headers=headers).status_code == 200
    assert client.post(f"/api/v1/agent-runs/{run_id}/cancel", headers=headers).status_code == 200
    detail = client.get(f"/api/v1/agent-runs/{run_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "cancelled"


def test_worker_rechecks_membership_before_using_tools(monkeypatch):
    from sqlalchemy import select

    from app.models.models import Membership
    async def forbidden(*args):
        raise AssertionError("revoked user must not use a tool")
    monkeypatch.setattr("app.services.agents.harness.execute_policy_scan", forbidden)
    with SessionLocal() as db:
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        membership = db.scalar(select(Membership).where(Membership.user_id == run.user_id))
        membership.status = "revoked"
        db.commit()
        asyncio.run(AgentHarness().execute(db, run.id))
        db.refresh(run)
        assert run.status == "failed"
        assert run.error_code == "verification_failed"
