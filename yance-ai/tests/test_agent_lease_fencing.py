"""Regression for acceptance ACC-08: a worker whose lease was reclaimed must stop.

Before the fix, _checkpoint only checked cancellation and requester
authorisation, so a stalled worker could keep writing to a run that another
worker had already reclaimed.
"""
import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from test_agent_harness import _queued_run

from app.core.db import SessionLocal
from app.models.models import AgentRun, AgentRunError

pytestmark = pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")


def _reclaim(db, run_id, new_owner):
    """Same state transition claim_next performs for an expired lease."""
    run = db.get(AgentRun, run_id)
    run.status, run.lease_owner = "planning", new_owner
    run.lease_expires_at = datetime.now(UTC) + timedelta(seconds=60)
    run.retry_count += 1
    db.commit()


@pytest.fixture(autouse=True)
def _retire_runs_created_here():
    """Leave no reclaimable runs behind for later claim_next-based tests."""
    created: list = []
    yield created
    with SessionLocal() as db:
        for run_id in created:
            run = db.get(AgentRun, run_id)
            if run is not None:
                run.status, run.lease_owner, run.lease_expires_at = "cancelled", None, None
        db.commit()


def test_checkpoint_raises_once_lease_is_owned_by_another_worker(_retire_runs_created_here):
    from app.services.agents import harness as harness_module

    with SessionLocal() as db_a, SessionLocal() as db_b:
        run, _, _ = _queued_run(db_a, suffix=uuid.uuid4().hex)
        _retire_runs_created_here.append(run.id)
        run.status, run.lease_owner = "running", "worker-A"
        run.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db_a.commit()
        _reclaim(db_b, run.id, "worker-B")

        token = harness_module.current_lease_owner.set("worker-A")
        try:
            with pytest.raises(harness_module.LeaseLost):
                harness_module.AgentHarness._checkpoint(db_a, run.id)
        finally:
            harness_module.current_lease_owner.reset(token)
        db_a.rollback()


def test_checkpoint_passes_for_current_lease_owner(_retire_runs_created_here):
    from app.services.agents import harness as harness_module

    with SessionLocal() as db:
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        _retire_runs_created_here.append(run.id)
        _reclaim(db, run.id, "worker-B")
        token = harness_module.current_lease_owner.set("worker-B")
        try:
            harness_module.AgentHarness._checkpoint(db, run.id)
        finally:
            harness_module.current_lease_owner.reset(token)
        db.rollback()


def test_execute_with_lost_lease_leaves_run_to_new_owner_without_recording_failure(_retire_runs_created_here):
    from app.services.agents import harness as harness_module

    with SessionLocal() as db:
        run, _, _ = _queued_run(db, suffix=uuid.uuid4().hex)
        _retire_runs_created_here.append(run.id)
        _reclaim(db, run.id, "worker-B")
        run_id = run.id

    token = harness_module.current_lease_owner.set("worker-A")
    try:
        with SessionLocal() as db:
            asyncio.run(harness_module.AgentHarness().execute(db, run_id))
    finally:
        harness_module.current_lease_owner.reset(token)

    with SessionLocal() as db:
        run = db.get(AgentRun, run_id)
        assert run.lease_owner == "worker-B"
        assert run.status == "planning"
        assert run.retry_count == 1
        errors = db.scalar(select(func.count()).select_from(AgentRunError).where(AgentRunError.agent_run_id == run_id))
        assert errors == 0
