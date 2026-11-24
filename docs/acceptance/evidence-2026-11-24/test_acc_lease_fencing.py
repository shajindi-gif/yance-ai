"""ACC-P2: no fencing token — a worker whose lease was reclaimed can still pass checkpoints and commit."""
import uuid, sys
from datetime import UTC, datetime, timedelta
sys.path.insert(0, "tests")
from test_agent_harness import _queued_run
from app.core.db import SessionLocal
from app.services.agents.harness import AgentHarness
from app.models.models import AgentRun


def test_zombie_worker_passes_checkpoint_after_lease_reclaimed():
    with SessionLocal() as db_a, SessionLocal() as db_b:
        run, _, _ = _queued_run(db_a, suffix=uuid.uuid4().hex)
        # worker A held the run, then stalled past its lease
        run.status, run.lease_owner = "running", "worker-A"
        run.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db_a.commit()
        # worker B reclaims it (same state transition claim_next performs for an expired lease)
        b_run = db_b.get(AgentRun, run.id)
        b_run.status, b_run.lease_owner = "planning", "worker-B"
        b_run.lease_expires_at = datetime.now(UTC) + timedelta(seconds=60)
        b_run.retry_count += 1
        db_b.commit()
        # worker A wakes up and continues: its checkpoint does not detect the lost lease
        AgentHarness._checkpoint(db_a, run.id)          # no exception => no fencing
        current = db_a.get(AgentRun, run.id)
        assert current.lease_owner == "worker-B"         # A is writing on a run owned by B
        db_a.rollback()
