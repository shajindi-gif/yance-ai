import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url


def main():
    if os.environ.get("APP_ENV") != "test":
        raise RuntimeError("Only isolated test environments are allowed")
    database = make_url(os.environ["DATABASE_URL"]).database
    if not (
        database
        and database == os.environ["YANCE_TEST_DATABASE_ACK"]
        and database.startswith("yance_")
        and ("test" in database.lower() or "e2e" in database.lower())
        and "prod" not in database.lower()
    ):
        raise RuntimeError("Explicit isolated V2 database acknowledgement required")
    output = Path(sys.argv[1]).resolve()
    if output.is_relative_to(Path.cwd().parent.resolve()):
        raise RuntimeError("Fixture credentials must stay outside the repository")

    sys.path.insert(0, str(Path.cwd() / "tests"))
    from fastapi.testclient import TestClient
    from test_core_workflow import _complete_profile, _register

    from app.core.db import SessionLocal
    from app.main import app
    from app.models.models import EligibilityRule, Opportunity, Policy, PolicyChunk, PolicyVersion
    from app.services.policies.eligibility import evaluate_opportunity

    with TestClient(app) as c:
        h, token = _register(c, "v2-browser-" + uuid.uuid4().hex)
        company = c.get("/api/v1/companies", headers=h).json()[0]
        profile = _complete_profile()
        assert (
            c.put(f"/api/v1/companies/{company['id']}/profile", headers=h, json=profile).status_code
            == 200
        )
        pub = c.post(f"/api/v1/companies/{company['id']}/profile/publish", headers=h).json()
        tenant = uuid.UUID(company["tenant_id"])
        with SessionLocal() as db:
            text = "合成验收原文：支持人工智能企业。须提供研发证明。"
            p = Policy(
                tenant_id=tenant,
                title="合成测试政策——不是真实资助项目",
                level="municipal",
                province="上海市",
                city="上海市",
                status="published",
                content=text,
                source_url="https://example.invalid/synthetic",
                effective_at=datetime.now(UTC) - timedelta(days=1),
                expires_at=datetime.now(UTC) + timedelta(days=90),
                deadline=datetime.now(UTC) + timedelta(days=30),
            )
            db.add(p)
            db.flush()
            v = PolicyVersion(
                policy_id=p.id,
                tenant_id=tenant,
                version=1,
                content_sha256=hashlib.sha256(text.encode()).hexdigest(),
                title=p.title,
                source_url=p.source_url,
                content=text,
                status="published",
            )
            db.add(v)
            db.flush()
            chunk = PolicyChunk(
                policy_id=p.id,
                policy_version_id=v.id,
                tenant_id=tenant,
                chunk_index=0,
                content=text,
                char_start=0,
                char_end=len(text),
                content_sha256=v.content_sha256,
            )
            db.add(chunk)
            for name, key, expected, quote in [
                ("行业条件", "industry", "人工智能", "支持人工智能企业"),
                ("研发证明", "rd_proof", "已具备", "须提供研发证明"),
            ]:
                db.add(
                    EligibilityRule(
                        policy_id=p.id,
                        policy_version_id=v.id,
                        tenant_id=tenant,
                        name=name,
                        fact_key=key,
                        operator="eq",
                        expected_json={"value": expected},
                        is_hard_gate=True,
                        source_quote=quote,
                        status="active",
                    )
                )
            o = Opportunity(
                tenant_id=tenant,
                company_id=uuid.UUID(company["id"]),
                policy_id=p.id,
                policy_version_id=v.id,
                profile_version_id=uuid.UUID(pub["id"]),
                title=p.title,
                score=0.8,
            )
            db.add(o)
            db.flush()
            evaluate_opportunity(db, o, pub["snapshot_json"])
            db.commit()
            oid = str(o.id)
        a = c.post(
            "/api/v1/applications",
            headers=h,
            json={
                "company_id": company["id"],
                "opportunity_id": oid,
                "title": "合成证据工作台浏览器验收",
            },
        )
        assert a.status_code == 201, a.text
        output.touch(mode=0o600, exist_ok=True)
        output.chmod(0o600)
        output.write_text(json.dumps({"token": token, "application_id": a.json()["id"]}))
        print("Synthetic browser fixture ready")


if __name__ == "__main__":
    main()
