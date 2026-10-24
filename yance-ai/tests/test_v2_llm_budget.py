"""Synthetic persisted output reservations; fake providers never use the network."""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_funding_os import _register
from test_v2_suggestion_evidence import _project

from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models.models import LLMInvocation, Membership
from app.services.llm.base import LLMRequest, LLMResponse
from app.services.llm.budget import LLMLimitExceeded, llm_budget_scope, reserve, settle
from app.services.llm.router import LLMRouter


def tenant():
    with TestClient(app) as client:
        _, me = _register(client, uuid.uuid4().hex)
        return uuid.UUID(me["tenant_id"]), uuid.UUID(me["id"])


def request():
    return LLMRequest(
        messages=[{"role": "user", "content": "合成问题"}], model="synthetic", max_tokens=100
    )


def test_concurrent_calls_cannot_exceed_tenant_daily_limit(monkeypatch):
    scope = tenant()
    monkeypatch.setattr(settings, "llm_daily_call_limit", 1)

    def claim(_):
        with llm_budget_scope(*scope):
            try:
                return reserve("deepseek", request())[0]
            except LLMLimitExceeded:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(claim, range(2)))
    assert sum(value is not None for value in outcomes) == 1
    # Another tenant has an independent budget.
    with llm_budget_scope(*tenant()):
        assert reserve("deepseek", request())[0]


def test_missing_usage_and_interruption_keep_reservation(monkeypatch):
    scope = tenant()
    monkeypatch.setattr(settings, "llm_daily_output_token_limit", 100)
    with llm_budget_scope(*scope):
        key, _ = reserve("deepseek", request())
        settle(key, LLMResponse(content="合成", model="synthetic", provider="deepseek"))
        with pytest.raises(LLMLimitExceeded):
            reserve("deepseek", request())
    with SessionLocal() as db:
        assert db.get(LLMInvocation, key).charged_output_tokens == 100


def test_success_settles_once_and_releases_only_known_unused_output(monkeypatch):
    scope = tenant()
    monkeypatch.setattr(settings, "llm_daily_output_token_limit", 110)
    with llm_budget_scope(*scope):
        key, _ = reserve("deepseek", request())
        settle(
            key,
            LLMResponse(content="合成", model="synthetic", provider="deepseek", output_tokens=10),
        )
        settle(
            key,
            LLMResponse(content="late", model="synthetic", provider="deepseek", output_tokens=0),
        )
        second, _ = reserve("deepseek", request())
        settle(second)
        with pytest.raises(LLMLimitExceeded):
            reserve("deepseek", request())
    with SessionLocal() as db:
        assert db.get(LLMInvocation, key).charged_output_tokens == 10
        assert db.get(LLMInvocation, second).status == "uncertain"


def test_router_requires_scope_and_preserves_cancelled_call():
    router = LLMRouter()

    class CancelProvider:
        async def complete(self, _request):
            raise asyncio.CancelledError()

    router.providers["deepseek"] = CancelProvider()
    with pytest.raises(LLMLimitExceeded):
        asyncio.run(router.complete(request(), provider="deepseek"))
    scope = tenant()
    with llm_budget_scope(*scope), pytest.raises(asyncio.CancelledError):
        asyncio.run(router.complete(request(), provider="deepseek"))
    with SessionLocal() as db:
        row = db.scalar(select(LLMInvocation).where(LLMInvocation.tenant_id == scope[0]))
        assert row.status == "uncertain" and row.charged_output_tokens == 100


def test_limits_and_revocation_prevent_provider_work(monkeypatch):
    scope = tenant()
    with llm_budget_scope(*scope):
        for invalid in (0, -1, True, 1.5, settings.llm_max_output_tokens + 1):
            invalid_request = request()
            invalid_request.max_tokens = invalid
            with pytest.raises(LLMLimitExceeded):
                reserve("deepseek", invalid_request)
        monkeypatch.setattr(settings, "llm_max_input_bytes", 1)
        with pytest.raises(LLMLimitExceeded):
            reserve("deepseek", request())
        monkeypatch.setattr(settings, "llm_max_input_bytes", 64000)
        with SessionLocal() as db:
            member = db.scalar(select(Membership).where(Membership.user_id == scope[1]))
            member.status = "revoked"
            db.commit()
        with pytest.raises(LLMLimitExceeded):
            reserve("deepseek", request())


def test_policy_api_budget_denial_is_429_not_a_fallback_conclusion(monkeypatch):
    from app.services.policy_engine import evaluator

    calls = []

    class Provider:
        async def complete(self, _request):
            calls.append(1)
            return LLMResponse(
                content='{"criteria":[{"criterion":"行业为人工智能","policy_quote":"支持人工智能企业"}]}',
                model="synthetic",
                provider="deepseek",
                output_tokens=20,
            )

    monkeypatch.setitem(evaluator._llm.providers, "deepseek", Provider())
    monkeypatch.setattr(settings, "llm_daily_call_limit", 1)
    with TestClient(app) as client:
        headers, _, app_id, _, _, policy_id = _project(client)
        detail = client.get(f"/api/v1/applications/{app_id}", headers=headers).json()
        response = client.post(
            "/api/v1/policy-engine/evaluate",
            headers=headers,
            json={
                "policy_id": str(policy_id),
                "company_id": detail["company_id"],
                "provider": "deepseek",
            },
        )
        assert response.status_code == 429, response.text
        assert calls == [1]
