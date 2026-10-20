import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.models import (
    AgentRetry,
    AgentRun,
    AgentRunError,
    Company,
    CompanyProfile,
    CompanyProfileVersion,
    Membership,
    PolicyScan,
    Task,
    Tenant,
    User,
    WorkflowRun,
)
from app.services.agents.harness import AgentHarness

pytestmark = pytest.mark.skipif(
    os.getenv("APP_ENV") != "test",
    reason="Agent Harness integration tests require the migrated PostgreSQL CI database",
)


def _queued_run(db, *, suffix: str) -> tuple[AgentRun, PolicyScan, Task]:
    tenant = Tenant(name=f"Harness Tenant {suffix}", slug=f"harness-{suffix}")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"harness-{suffix}@example.com",
        full_name="Harness Test",
        password_hash="not-used",
        role="owner",
    )
    db.add(user)
    db.flush()
    db.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner", status="active"))
    db.flush()
    company = Company(
        tenant_id=tenant.id,
        name=f"Harness Company {suffix}",
        province="上海市",
        city="上海市",
        industry="人工智能",
        metadata_json={},
    )
    db.add(company)
    db.flush()
    profile = CompanyProfile(
        tenant_id=tenant.id,
        company_id=company.id,
        status="published",
        draft_json={"industry": "人工智能", "province": "上海市"},
        completeness_score=20,
        published_version=1,
        published_at=datetime.now(UTC),
    )
    db.add(profile)
    db.flush()
    profile_version = CompanyProfileVersion(
        tenant_id=tenant.id,
        profile_id=profile.id,
        company_id=company.id,
        version=1,
        snapshot_json={"industry": "人工智能", "province": "上海市"},
        completeness_score=20,
        created_by=user.id,
    )
    db.add(profile_version)
    db.flush()
    scan = PolicyScan(
        tenant_id=tenant.id,
        company_id=company.id,
        profile_version_id=profile_version.id,
        requested_by=user.id,
        status="queued",
    )
    db.add(scan)
    db.flush()
    task = Task(
        tenant_id=tenant.id,
        user_id=user.id,
        company_id=company.id,
        scan_id=scan.id,
        task_type="policy_scan",
        title="Harness policy scan",
        status="queued",
        workflow_version="core-scan-v1",
        payment_status="free",
        progress=0,
    )
    db.add(task)
    db.flush()
    scan.task_id = task.id
    run = AgentHarness().enqueue_policy_scan(
        db,
        scan=scan,
        task=task,
        tenant_id=tenant.id,
        user_id=user.id,
    )
    db.commit()
    db.refresh(run)
    return run, scan, task


def test_expired_lease_is_reclaimed_and_recorded():
    with SessionLocal() as db:
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        run.status = "running"
        run.lease_owner = "dead-worker"
        run.lease_expires_at = datetime.now(UTC) - timedelta(seconds=5)
        db.commit()

        claimed_id = AgentHarness(lease_seconds=60).claim_next(db, "replacement-worker")
        assert claimed_id == run.id
        db.refresh(run)
        assert run.status == "planning"
        assert run.lease_owner == "replacement-worker"
        assert run.retry_count == 1
        retry = db.scalar(select(AgentRetry).where(AgentRetry.agent_run_id == run.id))
        assert retry is not None
        assert retry.reason_code == "lease_expired"
        assert retry.started_at is not None


def test_execution_failure_retries_then_fails_closed(monkeypatch):
    async def failing_matcher(*_args, **_kwargs):
        raise RuntimeError("sensitive provider response must not be persisted")

    monkeypatch.setattr(
        "app.services.agents.policy_scan.match_policies_for_company", failing_matcher
    )

    with SessionLocal() as db:
        run, scan, task = _queued_run(db, suffix=uuid.uuid4().hex)
        harness = AgentHarness(lease_seconds=60)

        for expected_retry_count in (1, 2):
            assert asyncio.run(harness.run_once(db, "failure-worker")) == run.id
            db.refresh(run)
            assert run.status == "queued"
            assert run.retry_count == expected_retry_count
            assert run.error_json == {"exception_type": "RuntimeError"}
            run.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()

        assert asyncio.run(harness.run_once(db, "failure-worker")) == run.id
        db.refresh(run)
        db.refresh(scan)
        db.refresh(task)
        workflow_run = db.scalar(select(WorkflowRun).where(WorkflowRun.id == run.workflow_run_id))
        assert run.status == "failed"
        assert workflow_run is not None and workflow_run.status == "failed"
        assert scan.status == "failed"
        assert task.status == "failed"
        assert (
            db.scalar(
                select(func.count())
                .select_from(AgentRetry)
                .where(AgentRetry.agent_run_id == run.id)
            )
            == 2
        )
        errors = db.scalars(select(AgentRunError).where(AgentRunError.agent_run_id == run.id)).all()
        assert len(errors) == 3
        assert all(error.details_json == {"exception_type": "RuntimeError"} for error in errors)
        assert all("sensitive" not in error.safe_message for error in errors)
