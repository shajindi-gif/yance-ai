"""Funding OS: structured funding facts, notifications, milestones, consultant."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    Application,
    Notification,
    Opportunity,
    Policy,
)
from app.services.funding.amounts import infer_funding_type, parse_support_amount
from app.services.notifications.deadlines import scan_deadlines


def _register(client: TestClient, prefix: str) -> tuple[dict, dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"FundingOS {prefix}",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_name": "Funding Owner",
            "owner_email": f"fundingos-{prefix}@example.com",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert response.status_code == 201, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = client.get("/api/v1/auth/me", headers=headers).json()
    return headers, me


def test_amount_parser_is_deterministic_and_conservative():
    parsed = parse_support_amount("最高500万")
    assert (parsed.amount_min, parsed.amount_max, parsed.parsed) == (None, 500.0, True)
    ranged = parse_support_amount("100万-300万元")
    assert (ranged.amount_min, ranged.amount_max) == (100.0, 300.0)
    ratio = parse_support_amount("按研发投入的30%补助，最高200万")
    assert ratio.amount_max == 200.0
    assert ratio.ratio == 30.0
    vague = parse_support_amount("另行确定")
    assert not vague.parsed and vague.amount_max is None
    assert infer_funding_type("资金补贴", "补助") == "grant"
    assert infer_funding_type("税收优惠", None) == "tax_incentive"
    assert infer_funding_type("另行确定", None) is None


def test_deadline_scan_emits_band_notifications_once_each():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, me = _register(client, suffix)
        company = client.get("/api/v1/companies", headers=headers).json()[0]
        due = datetime.now(UTC) + timedelta(days=6)
        application = Application(
            tenant_id=me["tenant_id"],
            company_id=company["id"],
            title=f"截止测试申报 {suffix}",
            status="preparing",
            due_at=due,
        )
        with SessionLocal() as db:
            db.add(application)
            db.commit()
            application_id = str(application.id)

        with SessionLocal() as db:
            first = scan_deadlines(db, tenant_id=uuid.UUID(me["tenant_id"]))
        assert first == 1
        with SessionLocal() as db:
            second = scan_deadlines(db, tenant_id=uuid.UUID(me["tenant_id"]))
        assert second == 0  # deduped per band

        with SessionLocal() as db:
            rows = list(
                db.scalars(
                    select(Notification).where(
                        Notification.tenant_id == uuid.UUID(me["tenant_id"])
                    )
                ).all()
            )
        assert len(rows) == 1
        assert rows[0].dedup_key == f"deadline:application:{application_id}:T-7"
        assert rows[0].severity == "warning"

        listed = client.get("/api/v1/notifications", headers=headers).json()
        assert len(listed) == 1
        read = client.post(f"/api/v1/notifications/{listed[0]['id']}/read", headers=headers)
        assert read.status_code == 200 and read.json()["read_at"]
        assert client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread"] == 0


def test_milestones_crud_and_tenant_isolation():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers_a, me_a = _register(client, f"a{suffix}")
        headers_b, _ = _register(client, f"b{suffix}")
        company = client.get("/api/v1/companies", headers=headers_a).json()[0]
        application = client.post(
            "/api/v1/applications",
            headers=headers_a,
            json={"company_id": company["id"], "title": f"里程碑测试 {suffix}"},
        )
        assert application.status_code == 201, application.text
        application_id = application.json()["id"]

        created = client.post(
            f"/api/v1/applications/{application_id}/milestones",
            headers=headers_a,
            json={"title": "提交软著申请", "due_at": (datetime.now(UTC) + timedelta(days=3)).isoformat()},
        )
        assert created.status_code == 201, created.text
        milestone_id = created.json()["id"]
        assert created.json()["status"] == "todo"

        cross_read = client.get(
            f"/api/v1/applications/{application_id}/milestones", headers=headers_b
        )
        assert cross_read.status_code == 404  # tenant B cannot see tenant A's application
        cross_patch = client.patch(
            f"/api/v1/milestones/{milestone_id}", headers=headers_b, json={"status": "done"}
        )
        assert cross_patch.status_code == 404

        patched = client.patch(
            f"/api/v1/milestones/{milestone_id}",
            headers=headers_a,
            json={"status": "done", "completion_note": "已获受理号"},
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "done" and patched.json()["completed_at"]

        deleted = client.delete(f"/api/v1/milestones/{milestone_id}", headers=headers_a)
        assert deleted.status_code == 204


def test_consultant_answers_with_citations_or_insufficient():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, me = _register(client, suffix)
        company = client.get("/api/v1/companies", headers=headers).json()[0]

        # No scan yet: must say INSUFFICIENT, never guess.
        overview = client.post(
            "/api/v1/consultant/ask",
            headers=headers,
            json={"company_id": company["id"], "question": "我们最近有哪些能申请的资金？"},
        )
        assert overview.status_code == 200
        payload = overview.json()
        assert payload["intent"] == "opportunities"
        assert payload["insufficient"] is True
        assert payload["blocks"] == []

        # Seed a real eligible opportunity with a policy citation source.
        with SessionLocal() as db:
            policy = Policy(
                title=f"测试AI资助专项 {suffix}",
                level="municipal",
                province="上海市",
                city="上海市",
                policy_type="subsidy",
                support_amount="最高500万",
                funding_amount_max=500.0,
                funding_type="grant",
                source_url="https://example.gov.cn/p/1",
                issuing_authority="测试局",
                deadline=datetime.now(UTC) + timedelta(days=20),
                status="published",
            )
            db.add(policy)
            db.flush()
            opportunity = Opportunity(
                tenant_id=uuid.UUID(me["tenant_id"]),
                company_id=uuid.UUID(company["id"]),
                policy_id=policy.id,
                title=policy.title,
                score=88.0,
                status="identified",
                eligibility_status="ELIGIBLE",
            )
            db.add(opportunity)
            db.commit()

        asked = client.post(
            "/api/v1/consultant/ask",
            headers=headers,
            json={"company_id": company["id"], "question": "有哪些可以申报？"},
        ).json()
        assert asked["insufficient"] is False
        assert asked["blocks"][0]["citation"]["source_url"] == "https://example.gov.cn/p/1"
        assert "500" in asked["blocks"][0]["detail"]["funding"]
        assert "500" in asked["summary"]  # estimated total mentions the official amount

        deadlines = client.post(
            "/api/v1/consultant/ask",
            headers=headers,
            json={"company_id": company["id"], "question": "距离截止还有什么没完成？"},
        ).json()
        assert deadlines["intent"] == "deadlines"


def test_application_inherits_policy_deadline_and_notifies():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, me = _register(client, suffix)
        company = client.get("/api/v1/companies", headers=headers).json()[0]
        deadline = datetime.now(UTC) + timedelta(days=10)
        with SessionLocal() as db:
            policy = Policy(
                title=f"截止联动测试政策 {suffix}",
                level="district",
                province="上海市",
                support_amount="最高100万",
                deadline=deadline,
                status="published",
            )
            db.add(policy)
            db.flush()
            db.add(
                Opportunity(
                    tenant_id=uuid.UUID(me["tenant_id"]),
                    company_id=uuid.UUID(company["id"]),
                    policy_id=policy.id,
                    title=policy.title,
                    score=80.0,
                    eligibility_status="ELIGIBLE",
                    policy_snapshot_json={"deadline": deadline.isoformat(), "title": policy.title},
                )
            )
            db.commit()
            opportunity_id = str(
                db.scalar(
                    select(Opportunity).where(Opportunity.title == policy.title)
                ).id
            )

        application = client.post(
            "/api/v1/applications",
            headers=headers,
            json={"company_id": company["id"], "opportunity_id": opportunity_id, "title": f"截止联动申报 {suffix}"},
        )
        assert application.status_code == 201, application.text
        # Deadline inherited from the official policy snapshot, no manual step.
        assert application.json()["due_at"] is not None
        application_id = application.json()["id"]

        # Manual override via PATCH.
        new_due = (datetime.now(UTC) + timedelta(days=2)).isoformat()
        patched = client.patch(
            f"/api/v1/applications/{application_id}",
            headers=headers,
            json={"due_at": new_due},
        )
        assert patched.status_code == 200
        assert patched.json()["due_at"][:10] == new_due[:10]

        scan = client.post("/api/v1/notifications/scan", headers=headers)
        assert scan.status_code == 200 and scan.json()["created"] >= 1
        titles = [n["title"] for n in client.get("/api/v1/notifications", headers=headers).json()]
        assert any("截止" in title for title in titles)


def test_funding_summary_and_amount_backfill():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, me = _register(client, suffix)
        company = client.get("/api/v1/companies", headers=headers).json()[0]

        with SessionLocal() as db:
            policy = Policy(
                title=f"回填测试政策 {suffix}",
                level="district",
                province="上海市",
                support_amount="100万-300万元",
                support_type="资金补贴",
                status="published",
            )
            db.add(policy)
            db.flush()
            db.add(
                Opportunity(
                    tenant_id=uuid.UUID(me["tenant_id"]),
                    company_id=uuid.UUID(company["id"]),
                    policy_id=policy.id,
                    title=policy.title,
                    score=75.0,
                    eligibility_status="POTENTIALLY_ELIGIBLE",
                )
            )
            db.commit()

        # Owner cannot manage the global knowledge base; use a direct service call
        # to exercise the same deterministic backfill logic the admin endpoint uses.
        from app.api.deps import Principal as _P
        from app.api.routes.policies import parse_support_amounts
        from app.models.models import User, UserRole

        with SessionLocal() as db:
            owner = db.scalar(select(User).where(User.email == f"fundingos-{suffix}@example.com"))
            owner.is_platform_admin = True
            db.commit()
            principal = _P(
                user=owner,
                tenant_id=uuid.UUID(me["tenant_id"]),
                role=UserRole.owner,
            )
            result = parse_support_amounts(principal=principal, db=db)
            owner.is_platform_admin = False
            db.commit()
        assert result["amounts_backfilled"] >= 1
        with SessionLocal() as db:
            policy_row = db.scalar(
                select(Policy).where(Policy.title == f"回填测试政策 {suffix}")
            )
        assert float(policy_row.funding_amount_min) == 100.0
        assert float(policy_row.funding_amount_max) == 300.0
        assert policy_row.funding_type == "grant"

        summary = client.get(
            "/api/v1/funding/summary", headers=headers, params={"company_id": company["id"]}
        )
        assert summary.status_code == 200
        body = summary.json()
        assert body["eligible_count"] == 1
        assert body["high_match_count"] == 1
        assert body["estimated_funding_available_wan"] == 300.0
        assert body["funding_amount_coverage"] == {"eligible": 1, "with_official_amount": 1}
        assert body["missing_evidence_count"] > 0
        assert "pipeline" in body and "recommended_opportunities" in body


def test_email_dispatch_disabled_by_default(monkeypatch):
    from app.core.config import settings
    from app.services.notifications import email as email_svc
    monkeypatch.setattr(settings, "email_enabled", False)
    assert email_svc.is_email_configured() is False
    with SessionLocal() as db:
        assert email_svc.dispatch_deadline_emails(db) == 0


def test_email_dispatch_sends_high_severity_only(monkeypatch):
    from app.core.config import settings
    from app.models.models import Notification
    from app.services.notifications import email as email_svc

    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, me = _register(client, suffix)
    # seed one warning + one info deadline notification
    with SessionLocal() as db:
        for sev, key in [("warning", f"deadline:test:{suffix}:warn"), ("info", f"deadline:test:{suffix}:info")]:
            db.add(Notification(
                tenant_id=uuid.UUID(me["tenant_id"]), kind="deadline", severity=sev,
                title=f"测试{sev}", body="正文", dedup_key=key,
            ))
        db.commit()

    sent = []
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(email_svc, "send_email", lambda to, subject, body: (sent.append((to, subject, body)) or True))
    with SessionLocal() as db:
        count = email_svc.dispatch_deadline_emails(db, tenant_id=uuid.UUID(me["tenant_id"]))
    assert count == 1  # only the warning band
    assert len(sent) == 1 and "测试warning" in sent[0][1]
    # idempotent: second dispatch does not re-email (dedup key suffixed)
    with SessionLocal() as db:
        assert email_svc.dispatch_deadline_emails(db, tenant_id=uuid.UUID(me["tenant_id"])) == 0
