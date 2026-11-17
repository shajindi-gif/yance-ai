"""Disposable local browser/latency fixtures; no production use or external calls."""

import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if os.environ.get("APP_ENV") != "test" or os.environ.get("LLM_DEFAULT_PROVIDER") != "mock":
    raise RuntimeError("test/mock required")
url = make_url(os.environ.get("DATABASE_URL", ""))
name = url.database or ""
if url.host not in {"localhost", "127.0.0.1"} or not name.endswith("_test") or "prod" in name or os.environ.get("YANCE_TEST_DATABASE_ACK") != name:
    raise RuntimeError("disposable database acknowledgement required")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Company, Membership, Policy, User, UserRole  # noqa: E402
from app.services.demo.scenarios import seed_investor_demo  # noqa: E402

with SessionLocal() as db:
    scenarios = seed_investor_demo(db)
    scenario = scenarios[0]
    # Seed function returns ORM demo scenarios, all explicitly is_demo.
    company = db.get(Company, scenario.company_id)
    user = User(
        tenant_id=company.tenant_id,
        email=f"workspace-{uuid.uuid4().hex}@example.invalid",
        full_name="合成验收用户",
        password_hash="disabled-local-browser-fixture",
        role=UserRole.owner,
    )
    db.add(user)
    db.flush()
    db.add(Membership(tenant_id=company.tenant_id, user_id=user.id, role=UserRole.owner))
    db.commit()
    token = create_access_token(user_id=user.id, tenant_id=company.tenant_id, role="owner")
    policy = db.get(Policy, scenario.policy_id) if hasattr(scenario, "policy_id") else None
    fixture = {
        "token": token,
        "company_id": str(company.id),
        "application_id": str(scenario.application_id),
        "synthetic": True,
    }
path = Path("/tmp/yance-workspace-browser.json")
path.write_text(json.dumps(fixture))
path.chmod(0o600)
with TestClient(app) as client:
    headers = {"Authorization": f"Bearer {token}"}
    samples = []
    for n in range(105):
        start = time.perf_counter()
        response = client.get("/api/v1/workspace/home", headers=headers)
        assert response.status_code == 200, response.text
        if n >= 5:
            samples.append((time.perf_counter() - start) * 1000)
    report = {
        "fixture": "seed_investor_demo, one synthetic scenario tenant",
        "samples": len(samples),
        "warmup": 5,
        "transport": "FastAPI TestClient loopback in-process + PG18 127.0.0.1",
        "p50_ms": statistics.median(samples),
        "p95_ms": sorted(samples)[94],
        "max_ms": max(samples),
        "production_claim": False,
    }
Path("../docs/workspace-ask-v1/home-latency.json").write_text(json.dumps(report, indent=2) + "\n")
print("Synthetic fixture saved outside Git; latency report written. No external calls.")

# Separate source-complete synthetic project for browser evidence reading.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_v2_suggestion_evidence import _project  # noqa: E402

with TestClient(app) as client:
    headers, _, aid, _, _, policy_id = _project(client)
    detail = client.get(f"/api/v1/applications/{aid}", headers=headers).json()
    with SessionLocal() as db:
        company = db.get(Company, uuid.UUID(detail["company_id"]))
        company.name = "DEMO · 问衍策验收企业（合成）"
        db.commit()
    fixture = {
        "token": headers["Authorization"].removeprefix("Bearer "),
        "company_id": detail["company_id"],
        "application_id": aid,
        "policy_id": str(policy_id),
        "synthetic": True,
    }
    path.write_text(json.dumps(fixture))
