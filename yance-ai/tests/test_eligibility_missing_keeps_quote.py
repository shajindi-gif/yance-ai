"""NEED_MORE with a verified rule quote still persists Evidence (customer brief)."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    EligibilityRule,
    Evidence,
    Opportunity,
    Policy,
    PolicyChunk,
    PolicyVersion,
)
from app.services.policies.eligibility import evaluate_opportunity

pytestmark = pytest.mark.skipif(
    os.getenv("APP_ENV") != "test",
    reason="Requires migrated PostgreSQL test database",
)


def test_missing_enterprise_fact_still_attaches_verified_quote():
    suffix = uuid.uuid4().hex
    quote = "支持人工智能企业研发费用投入"
    policy_text = f"{quote}，申报需提供研发费用专项审计报告。"

    with TestClient(app) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "company_name": f"Missing Quote {suffix}",
                "industry": "人工智能",
                "province": "上海市",
                "city": "上海市",
                "owner_email": f"missing-quote-{suffix}@example.com",
                "owner_name": "Owner",
                "owner_password": "integration-password-123",
                "agreed_terms_version": "test-terms",
            },
        )
        assert registered.status_code == 201, registered.text
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
        company = client.get("/api/v1/companies", headers=headers).json()[0]
        tenant_id = uuid.UUID(company["tenant_id"])
        company_id = uuid.UUID(company["id"])
        assert (
            client.put(
                f"/api/v1/companies/{company['id']}/profile",
                headers=headers,
                json={
                    "industry": "人工智能",
                    "province": "上海市",
                    "city": "上海市",
                    "registered_address": "上海市徐汇区测试路 1 号",
                    "founded_date": "2022-01-15",
                    "company_scale": "小型",
                    "employee_count": 42,
                    "revenue_stage": "成长期",
                    "annual_revenue": 12_000_000,
                    "funding_stage": "A轮",
                    "high_tech_status": "准备申报",
                    "tech_sme_status": "已认定",
                    "specialized_sme_status": "未认定",
                    "intellectual_property": ["软件著作权 3 项"],
                    "core_products": ["企业知识管理平台"],
                    "rd_summary": "持续研发。",
                    "talent_summary": "研发人员 20 人。",
                    "projects": ["企业知识智能化项目"],
                    "current_needs": ["研发补贴"],
                },
            ).status_code
            == 200
        )
        published = client.post(
            f"/api/v1/companies/{company['id']}/profile/publish", headers=headers
        )
        assert published.status_code == 201, published.text
        profile_version_id = uuid.UUID(published.json()["id"])

    with SessionLocal() as db:
        policy = Policy(
            tenant_id=tenant_id,
            title="缺失事实仍保留引用",
            issuing_authority="测试机关",
            level="municipal",
            province="上海市",
            city="上海市",
            industry="人工智能",
            policy_type="subsidy",
            source_url="https://policy.example.invalid/missing-fact",
            content=policy_text,
            effective_at=datetime.now(UTC) - timedelta(days=10),
            expires_at=datetime.now(UTC) + timedelta(days=100),
            status="published",
            embedding=[0.1] * 1024,
        )
        db.add(policy)
        db.flush()
        version = PolicyVersion(
            policy_id=policy.id,
            tenant_id=tenant_id,
            version=1,
            content_sha256=hashlib.sha256(policy_text.encode()).hexdigest(),
            title=policy.title,
            issuer=policy.issuing_authority,
            region="上海市",
            industry=policy.industry,
            policy_type=policy.policy_type,
            source_url=policy.source_url,
            content=policy_text,
            status="published",
        )
        db.add(version)
        db.flush()
        db.add(
            PolicyChunk(
                policy_id=policy.id,
                policy_version_id=version.id,
                tenant_id=tenant_id,
                chunk_index=0,
                content=policy_text,
                char_start=0,
                char_end=len(policy_text),
                content_sha256=hashlib.sha256(policy_text.encode()).hexdigest(),
                metadata_json={},
                embedding=[0.1] * 1024,
            )
        )
        db.add(
            EligibilityRule(
                policy_id=policy.id,
                policy_version_id=version.id,
                name="研发费用占比",
                fact_key="rd_expense_ratio",
                operator="gte",
                expected_json={"value": 5},
                is_hard_gate=True,
                source_quote=quote,
                article="申报条件",
                status="active",
            )
        )
        opportunity = Opportunity(
            tenant_id=tenant_id,
            company_id=company_id,
            policy_id=policy.id,
            policy_version_id=version.id,
            profile_version_id=profile_version_id,
            title=policy.title,
            score=0.5,
            eligibility_status="NEED_MORE_INFORMATION",
            policy_snapshot_json={
                "title": policy.title,
                "source_url": policy.source_url,
                "policy_version_id": str(version.id),
            },
        )
        db.add(opportunity)
        db.commit()
        opportunity_id = opportunity.id

        result = evaluate_opportunity(
            db,
            opportunity,
            {"industry": "人工智能", "province": "上海市", "city": "上海市"},
        )
        db.commit()
        assert result.status == "NEED_MORE_INFORMATION"
        evidence = list(
            db.scalars(
                select(Evidence).where(
                    Evidence.opportunity_id == opportunity_id,
                    Evidence.verified.is_(True),
                )
            ).all()
        )
        assert len(evidence) == 1
        assert evidence[0].quote == quote
