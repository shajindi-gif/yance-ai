"""Two-session/late-provider synthetic regressions; no external providers."""

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from test_agent_harness import _queued_run

from app.core.db import SessionLocal
from app.models.models import AgentRun, AgentRunError, Company, Deliverable
from app.services.agents.harness import AgentHarness

pytestmark = pytest.mark.skipif(
    os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required"
)


def test_reclaimed_attempt_cannot_commit_domain_results_and_new_attempt_resumes(monkeypatch):
    harness = AgentHarness()
    with SessionLocal() as old, SessionLocal() as replacement:
        run, _, task = _queued_run(old, suffix=uuid.uuid4().hex)
        run_id, company_id, task_id = run.id, task.company_id, task.id
        original_name = old.get(Company, company_id).name
        harness.claim_next(old, "old-worker", run_id=run_id)
        did_reclaim = False

        async def late_result(db, company, *_args, **_kwargs):
            nonlocal did_reclaim
            if not did_reclaim:
                did_reclaim = True
                current = replacement.get(AgentRun, run_id)
                current.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
                replacement.commit()
                assert harness.claim_next(replacement, "new-worker", run_id=run_id) == run_id
                company.name = "stale provider result must roll back"
                db.commit()  # The flush/commit guard must reject this helper write.
            return []

        monkeypatch.setattr(
            "app.services.agents.policy_scan.match_policies_for_company", late_result
        )
        asyncio.run(harness.execute(old, run_id))
        with SessionLocal() as check:
            assert check.get(Company, company_id).name == original_name
            assert check.get(AgentRun, run_id).lease_owner == "new-worker"
            assert (
                check.scalar(
                    select(func.count())
                    .select_from(AgentRunError)
                    .where(AgentRunError.agent_run_id == run_id)
                )
                == 0
            )
        asyncio.run(harness.execute(replacement, run_id))
        with SessionLocal() as check:
            assert check.get(AgentRun, run_id).status == "completed"
            assert (
                check.scalar(
                    select(func.count())
                    .select_from(Deliverable)
                    .where(Deliverable.task_id == task_id)
                )
                == 1
            )
        # Re-entering an already completed execution cannot add a second artifact.
        asyncio.run(harness.execute(replacement, run_id))


def test_old_exception_cannot_requeue_replacement_completed_run(monkeypatch):
    harness = AgentHarness()
    with SessionLocal() as old, SessionLocal() as replacement:
        run, _, _ = _queued_run(old, suffix=uuid.uuid4().hex)
        run_id = run.id
        harness.claim_next(old, "old-worker", run_id=run_id)

        async def interrupted(*_args, **_kwargs):
            current = replacement.get(AgentRun, run_id)
            current.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            replacement.commit()
            harness.claim_next(replacement, "replacement", run_id=run_id)
            current.status = "completed"  # Simulated accepted result on the new attempt.
            current.lease_token = None
            replacement.commit()
            raise RuntimeError("synthetic late provider failure")

        monkeypatch.setattr(
            "app.services.agents.policy_scan.match_policies_for_company", interrupted
        )
        asyncio.run(harness.execute(old, run_id))
        with SessionLocal() as check:
            current = check.get(AgentRun, run_id)
            assert current.status == "completed"
            assert current.retry_count == 1  # Only the real lease recovery, no old-worker retry.
            assert (
                check.scalar(
                    select(func.count())
                    .select_from(AgentRunError)
                    .where(AgentRunError.agent_run_id == run_id)
                )
                == 0
            )


def test_execute_cannot_adopt_another_sessions_active_lease(monkeypatch):
    async def forbidden(*_args):
        raise AssertionError("active lease was adopted")

    monkeypatch.setattr("app.services.agents.harness.execute_policy_scan", forbidden)
    with SessionLocal() as owner, SessionLocal() as other:
        run, _, _ = _queued_run(owner, suffix=uuid.uuid4().hex)
        harness = AgentHarness()
        harness.claim_next(owner, "owner", run_id=run.id)
        asyncio.run(harness.execute(other, run.id))
        owner.refresh(run)
        assert run.status == "planning" and run.lease_owner == "owner"
        run.status = "cancelled"
        owner.commit()
