import json
import os
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from test_core_workflow import _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import AgentRun, Opportunity, Policy, Task, User

url = make_url(os.environ["DATABASE_URL"])
assert os.environ["APP_ENV"] == "test" and url.host == "127.0.0.1"
assert url.database == os.environ["YANCE_TEST_DATABASE_ACK"]
assert url.database.startswith("yance_") and "test" in url.database and "prod" not in url.database
path = Path(sys.argv[1]).resolve()
assert not path.is_relative_to(Path(__file__).resolve().parents[2])
data = json.loads(path.read_text())
headers = {"Authorization": "Bearer " + data["token"]}
with TestClient(app) as client:
    company = client.get("/api/v1/companies", headers=headers).json()[0]
    tenant = uuid.UUID(company["tenant_id"])
    me = client.get("/api/v1/auth/me", headers=headers).json()
    with SessionLocal() as db:
        policy = db.scalar(select(Policy).where(Policy.tenant_id == tenant))
        opportunity = Opportunity(
            tenant_id=tenant,
            company_id=uuid.UUID(company["id"]),
            policy_id=policy.id,
            title="合成设计验收机会",
            eligibility_status="NEED_MORE_INFORMATION",
        )
        task = Task(
            tenant_id=tenant,
            company_id=uuid.UUID(company["id"]),
            user_id=uuid.UUID(me["id"]),
            task_type="policy_report",
            title="合成设计验收任务",
            status="queued",
        )
        run = AgentRun(
            tenant_id=tenant,
            user_id=uuid.UUID(me["id"]),
            agent_name="合成设计验收任务",
            provider="mock",
            model="mock",
            status="queued",
        )
        db.add_all([opportunity, task, run])
        db.commit()
        data.update(
            company_id=company["id"],
            opportunity_id=str(opportunity.id),
            task_id=str(task.id),
            agent_run_id=str(run.id),
        )
    admin_headers, admin_token = _register(client, "design-admin-" + uuid.uuid4().hex)
    admin = client.get("/api/v1/auth/me", headers=admin_headers).json()
    with SessionLocal() as db:
        db.get(User, uuid.UUID(admin["id"])).is_platform_admin = True
        db.commit()
    created = client.post(
        "/api/v1/admin/evals/runs", headers=admin_headers, json={"eval_type": "hallucination_eval"}
    )
    assert created.status_code == 201, created.status_code
    data["admin_token"] = admin_token
    data["eval_run_id"] = created.json()["runs"][0]["id"]
path.write_text(json.dumps(data))
path.chmod(0o600)
print("Five synthetic detail fixtures ready")
