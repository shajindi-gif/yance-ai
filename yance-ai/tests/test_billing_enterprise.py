import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import ApiKey, Membership, UsageRecord, User, UserRole


def _register(client: TestClient, prefix: str) -> tuple[dict[str, str], dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Enterprise {prefix}",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_name": "Enterprise Owner",
            "owner_email": f"enterprise-{prefix}@example.com",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert response.status_code == 201, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    me = client.get("/api/v1/auth/me", headers=headers).json()
    return headers, me


def test_plan_catalog_free_subscription_and_resource_quota_are_database_backed():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, _ = _register(client, suffix)
        plans = client.get("/api/v1/billing/plans")
        assert plans.status_code == 200
        assert [item["code"] for item in plans.json()["items"]] == [
            "free",
            "pro",
            "business",
            "enterprise",
        ]
        assert plans.json()["items"][0]["price"]["unit_amount"] == 0
        assert all(item["price"] is None for item in plans.json()["items"][1:])

        overview = client.get("/api/v1/billing/overview", headers=headers)
        assert overview.status_code == 200, overview.text
        payload = overview.json()
        assert payload["plan"]["code"] == "free"
        assert payload["subscription"]["provider"] == "internal"
        usage = {item["meter"]: item for item in payload["usage"]}
        assert usage["companies"]["used"] == 1
        assert usage["users"]["used"] == 1
        assert payload["paid_plan_checkout_available"] is False

        second = client.post("/api/v1/companies", headers=headers, json={"name": "Second"})
        assert second.status_code == 201, second.text
        blocked = client.post("/api/v1/companies", headers=headers, json={"name": "Third"})
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == {
            "code": "quota_exceeded",
            "meter": "companies",
            "used": 2,
            "requested": 1,
            "limit": 2,
            "reset_at": blocked.json()["detail"]["reset_at"],
            "scope": "plan",
        }


def test_api_key_is_hashed_scoped_restricted_and_revocable():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, me = _register(client, suffix)
        created = client.post(
            "/api/v1/enterprise/api-keys",
            headers=headers,
            json={"name": "Read integration", "scopes": ["read"]},
        )
        assert created.status_code == 201, created.text
        raw_key = created.json()["secret"]
        assert raw_key.startswith("yance_live_")
        with SessionLocal() as db:
            stored = db.scalar(select(ApiKey).where(ApiKey.id == uuid.UUID(created.json()["id"])))
            assert stored
            assert stored.secret_hash != raw_key
            assert len(stored.secret_hash) == 64
            user = db.get(User, uuid.UUID(me["id"]))
            membership = db.scalar(
                select(Membership).where(Membership.user_id == user.id)
            )
            user.role = UserRole.viewer
            membership.role = UserRole.owner
            db.commit()

        listed = client.get("/api/v1/enterprise/api-keys", headers=headers)
        assert listed.status_code == 200
        assert "secret" not in listed.json()["items"][0]
        assert "secret_hash" not in listed.json()["items"][0]

        key_headers = {"X-API-Key": raw_key}
        assert client.get("/api/v1/companies", headers=key_headers).status_code == 200
        assert client.post("/api/v1/companies", headers=key_headers, json={"name": "Denied"}).status_code == 403
        assert client.get("/api/v1/billing/overview", headers=key_headers).status_code == 403

        revoked = client.post(
            f"/api/v1/enterprise/api-keys/{created.json()['id']}/revoke", headers=headers
        )
        assert revoked.status_code == 200
        assert client.get("/api/v1/companies", headers=key_headers).status_code == 401


def test_usage_budget_is_idempotent_and_cannot_expand_plan():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, me = _register(client, suffix)
        overview = client.get("/api/v1/billing/overview", headers=headers).json()
        budget = client.post(
            "/api/v1/billing/budgets",
            headers=headers,
            json={
                "scope_type": "organization",
                "meter_key": "reports",
                "hard_limit": 1,
                "warning_threshold": 1,
            },
        )
        assert budget.status_code == 201, budget.text
        from app.services.billing.usage import QuotaExceeded, consume_usage, consume_usage_once

        with SessionLocal() as db:
            first, first_created = consume_usage_once(
                db,
                tenant_id=uuid.UUID(me["tenant_id"]),
                meter="reports",
                quantity=1,
                idempotency_key=f"report:{suffix}",
                user_id=uuid.UUID(me["id"]),
            )
            duplicate, duplicate_created = consume_usage_once(
                db,
                tenant_id=uuid.UUID(me["tenant_id"]),
                meter="reports",
                quantity=1,
                idempotency_key=f"report:{suffix}",
                user_id=uuid.UUID(me["id"]),
            )
            assert first.id == duplicate.id
            assert first_created is True
            assert duplicate_created is False
            db.commit()
            try:
                consume_usage(
                    db,
                    tenant_id=uuid.UUID(me["tenant_id"]),
                    meter="reports",
                    quantity=1,
                    idempotency_key=f"report:{suffix}:second",
                    user_id=uuid.UUID(me["id"]),
                )
            except QuotaExceeded as exc:
                assert exc.scope == "organization"
            else:
                raise AssertionError("organization budget must remain a hard upper bound")
            assert db.scalar(
                select(UsageRecord).where(
                    UsageRecord.tenant_id == uuid.UUID(me["tenant_id"]),
                    UsageRecord.idempotency_key == f"report:{suffix}:second",
                )
            ) is None
        assert overview["plan"]["limits"]["reports"] == 2


def test_retention_export_deletion_and_audit_are_tenant_scoped_and_honest():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, _ = _register(client, suffix)
        other_headers, _ = _register(client, f"other-{suffix}")

        hold = client.put(
            "/api/v1/enterprise/retention",
            headers=headers,
            json={
                "document_days": 365,
                "agent_trace_days": 180,
                "analytics_days": 365,
                "audit_days": 730,
                "legal_hold": True,
                "legal_hold_reason": "Active diligence preservation",
            },
        )
        assert hold.status_code == 200, hold.text
        assert hold.json()["enforcement_worker_available"] is False
        blocked = client.post(
            "/api/v1/enterprise/deletion-request", headers=headers, json={"reason": "test"}
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "legal_hold"

        release = client.put(
            "/api/v1/enterprise/retention",
            headers=headers,
            json={
                "document_days": 365,
                "agent_trace_days": 180,
                "analytics_days": 365,
                "audit_days": 730,
                "legal_hold": False,
                "legal_hold_reason": None,
            },
        )
        assert release.status_code == 200
        exported = client.post("/api/v1/enterprise/exports", headers=headers)
        assert exported.status_code == 202, exported.text
        export_id = exported.json()["id"]
        download = client.get(
            f"/api/v1/enterprise/exports/{export_id}/download", headers=headers
        )
        assert download.status_code == 200
        payload = download.json()
        serialized_keys = set()

        def collect_keys(value):
            if isinstance(value, dict):
                serialized_keys.update(value)
                for child in value.values():
                    collect_keys(child)
            elif isinstance(value, list):
                for child in value:
                    collect_keys(child)

        collect_keys(payload)
        assert not {"password_hash", "secret_hash", "raw_response", "object_key"} & serialized_keys
        assert client.get(
            f"/api/v1/enterprise/exports/{export_id}/download", headers=other_headers
        ).status_code == 404

        scheduled = client.post(
            "/api/v1/enterprise/deletion-request",
            headers=headers,
            json={"reason": "owner_requested"},
        )
        assert scheduled.status_code == 202
        assert scheduled.json()["execution_worker_available"] is False
        assert scheduled.json()["blockers"]
        canceled = client.post(
            f"/api/v1/enterprise/deletion-request/{scheduled.json()['id']}/cancel",
            headers=headers,
        )
        assert canceled.status_code == 200
        assert canceled.json()["status"] == "canceled"

        audit = client.get("/api/v1/enterprise/audit-logs", headers=headers)
        assert audit.status_code == 200
        entries = audit.json()["items"]
        assert len(entries) >= 5
        assert all(item["entry_hash"] for item in entries)


def test_feature_flags_are_platform_managed_tenant_scoped_and_audited():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        platform_headers, platform_me = _register(client, f"platform-{suffix}")
        tenant_headers, tenant_me = _register(client, f"tenant-{suffix}")
        with SessionLocal() as db:
            platform_user = db.get(User, uuid.UUID(platform_me["id"]))
            assert platform_user
            platform_user.is_platform_admin = True
            db.commit()

        denied = client.get("/api/v1/admin/feature-flags", headers=tenant_headers)
        assert denied.status_code == 403
        configured = client.put(
            "/api/v1/admin/feature-flags/new_policy_agent",
            headers=platform_headers,
            json={
                "description": "Enable the versioned policy agent for selected tenants.",
                "enabled_by_default": False,
                "status": "active",
            },
        )
        assert configured.status_code == 200, configured.text
        assert configured.json()["enabled_by_default"] is False
        effective = client.get("/api/v1/enterprise/feature-flags", headers=tenant_headers)
        assert effective.status_code == 200
        assert effective.json()["flags"]["new_policy_agent"] is False

        target_tenant_id = tenant_me["tenant_id"]
        overridden = client.put(
            f"/api/v1/admin/feature-flags/new_policy_agent/tenants/{target_tenant_id}",
            headers=platform_headers,
            json={"enabled": True, "reason": "controlled pilot"},
        )
        assert overridden.status_code == 200, overridden.text
        assert overridden.json()["enabled"] is True
        assert client.get(
            "/api/v1/enterprise/feature-flags", headers=tenant_headers
        ).json()["flags"]["new_policy_agent"] is True

        listed = client.get("/api/v1/admin/feature-flags", headers=platform_headers)
        assert listed.status_code == 200
        assert listed.json()["tenant_overrides"][0]["tenant_id"] == target_tenant_id
        removed = client.delete(
            f"/api/v1/admin/feature-flags/new_policy_agent/tenants/{target_tenant_id}",
            headers=platform_headers,
            params={"reason": "pilot complete"},
        )
        assert removed.status_code == 204
        assert client.get(
            "/api/v1/enterprise/feature-flags", headers=tenant_headers
        ).json()["flags"]["new_policy_agent"] is False

        audit = client.get("/api/v1/enterprise/audit-logs", headers=tenant_headers)
        actions = {entry["action"] for entry in audit.json()["items"]}
        assert "feature_flag.tenant_override_set" in actions
        assert "feature_flag.tenant_override_removed" in actions
