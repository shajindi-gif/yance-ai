"""Synthetic, offline gateway and two-tenant API contracts; not business accuracy."""

import asyncio
import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import select
from test_funding_os import _register
from test_v2_suggestion_evidence import _project

from app.api.routes import workspace
from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models.models import Conversation, ConversationMessage, Membership, UserRole
from app.services.llm.base import LLMRequest, LLMResponse
from app.services.llm.gateway import (
    InsufficientEvidence,
    LLMGateway,
    TaskType,
    route_for,
    verify_quotes,
)
from app.services.llm.router import LLMRouter


class Answer(BaseModel):
    value: str


def test_routes_and_production_provider_boundary(monkeypatch):
    monkeypatch.setattr(settings, "llm_default_provider", "mock")
    assert route_for(TaskType.chat_answer).primary.provider == "mock"
    monkeypatch.setattr(settings, "app_env", "production")
    assert route_for(TaskType.chat_answer).primary.provider == "qwen"
    assert route_for(TaskType.extract_criteria).primary.provider == "deepseek"
    monkeypatch.setattr(
        settings,
        "llm_task_routes",
        json.dumps(
            {
                "chat_answer": {
                    "primary": {"provider": "openai", "model": "gpt-4o-mini"},
                    "fallback": {"provider": "qwen", "model": "qwen-plus"},
                }
            }
        ),
    )
    with pytest.raises(ValueError, match="not allowed"):
        route_for(TaskType.chat_answer)
    with pytest.raises(ValueError, match="not allowed"):
        asyncio.run(LLMRouter().complete(LLMRequest(messages=[], model="mock"), provider="mock"))


def test_quote_gate_drops_whole_false_claim():
    result, rejected = verify_quotes(
        {
            "claims": [
                {"text": "fabricated", "policy_quote": "不存在"},
                {"text": "ok", "policy_quote": "研发 费用"},
                {"text": "empty", "policy_quote": " "},
            ]
        },
        "研发\n费用",
    )
    assert rejected == 2 and result["claims"] == [{"text": "ok", "policy_quote": "研发 费用"}]


def test_schema_retry_and_transient_fallback(monkeypatch):
    gateway = LLMGateway()
    seen = []

    async def complete(request, provider):
        seen.append((provider, request.model, request.response_format))
        if len(seen) == 1:
            raise httpx.ReadTimeout("synthetic")
        return LLMResponse(content='{"value":"ok"}', model=request.model, provider=provider)

    monkeypatch.setattr(
        settings,
        "llm_task_routes",
        json.dumps(
            {
                "chat_answer": {
                    "primary": {"provider": "deepseek", "model": "deepseek-chat"},
                    "fallback": {"provider": "qwen", "model": "qwen-plus"},
                    "stream": True,
                }
            }
        ),
    )
    monkeypatch.setattr(gateway.router, "complete", complete)
    result = asyncio.run(gateway.complete(TaskType.chat_answer, [], schema=Answer))
    assert result.raw["fallback_used"] and [x[0] for x in seen] == ["deepseek", "qwen"]
    assert seen[1][2]["type"] == "json_schema"
    seen.clear()

    async def invalid(request, provider):
        seen.append(1)
        return LLMResponse(content="not json", model=request.model, provider=provider)

    monkeypatch.setattr(gateway.router, "complete", invalid)
    with pytest.raises(InsufficientEvidence):
        asyncio.run(gateway.complete(TaskType.chat_answer, [], schema=Answer))
    assert len(seen) == 2


def test_client_errors_never_fallback(monkeypatch):
    gateway = LLMGateway()
    calls = []

    async def fail(request, provider):
        calls.append(provider)
        raise httpx.HTTPStatusError(
            "synthetic",
            request=httpx.Request("POST", "https://invalid.test"),
            response=httpx.Response(401),
        )

    monkeypatch.setattr(gateway.router, "complete", fail)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(gateway.complete(TaskType.chat_answer, []))
    assert len(calls) == 1


def test_stream_mock_and_cancellation_no_network(monkeypatch):
    gateway = LLMGateway()

    async def fake(request, provider):
        return LLMResponse(content='{"value":"合成"}', model="mock", provider="mock")

    monkeypatch.setattr(gateway.router, "complete", fake)

    async def collect():
        return [
            token
            async for token in gateway.complete_stream(TaskType.chat_answer, [], schema=Answer)
        ]

    assert asyncio.run(collect()) == ['{"value":"合成"}']


def test_workspace_isolation_rules_replay_and_viewer(monkeypatch):
    monkeypatch.setattr(settings, "workspace_ask_enabled", True)
    with TestClient(app) as client:
        a, _, application, _, _, _ = _project(client)
        b, _ = _register(client, uuid.uuid4().hex)
        detail = client.get(f"/api/v1/applications/{application}", headers=a).json()
        company_id = detail["company_id"]
        home = client.get("/api/v1/workspace/home", headers=a)
        assert home.status_code == 200
        assert len(home.json()["cards"]) == 5
        assert (
            client.get(f"/api/v1/workspace/home?company_id={company_id}", headers=b).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/ask", headers=b, json={"company_id": company_id, "question": "缺什么材料"}
            ).status_code
            == 404
        )
        request = {
            "company_id": company_id,
            "question": "缺什么材料",
            "request_id": str(uuid.uuid4()),
        }
        response = client.post("/api/v1/ask", headers=a, json=request)
        assert response.status_code == 200 and "event: done" in response.text
        assert "stored_records" in response.text
        assert client.post("/api/v1/ask", headers=a, json=request).status_code == 409
        cid = request["request_id"]
        assert client.get(f"/api/v1/workspace/conversations/{cid}", headers=b).status_code == 404
        assert client.get(f"/api/v1/workspace/conversations/{cid}", headers=a).status_code == 200
        with SessionLocal() as db:
            row = db.get(Conversation, uuid.UUID(cid))
            assert row.status == "completed"
            assert (
                len(
                    db.scalars(
                        select(ConversationMessage).where(
                            ConversationMessage.conversation_id == row.id
                        )
                    ).all()
                )
                == 2
            )
            member = db.scalar(select(Membership).where(Membership.user_id == row.user_id))
            member.role = UserRole.viewer
            db.commit()
        assert (
            client.post(
                "/api/v1/ask", headers=a, json={**request, "request_id": str(uuid.uuid4())}
            ).status_code
            == 403
        )
        assert client.get("/api/v1/workspace/home", headers=a).json()["can_ask"] is False


def test_ask_rejects_invented_quotes_and_failure_preserves_question(monkeypatch):
    monkeypatch.setattr(settings, "workspace_ask_enabled", True)
    source = {
        "index": 1,
        "policy_id": str(uuid.uuid4()),
        "version_id": str(uuid.uuid4()),
        "title": "合成条款",
        "source_url": "https://example.invalid",
        "policy_quote": "研发费用占比不低于百分之五",
        "char_start": 0,
    }
    monkeypatch.setattr(workspace, "sources_for", lambda *args: [source])

    async def stream(*args, **kwargs):
        yield json.dumps(
            {
                "claims": [
                    {"text": "保证获批", "source": 1, "policy_quote": "研发费用占比不低于百分之五"},
                    {
                        "text": "研发费用占比不低于百分之五",
                        "source": 1,
                        "policy_quote": "研发费用占比不低于百分之五",
                    },
                ]
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(workspace.gateway, "complete_stream", stream)
    with TestClient(app) as client:
        headers, _, aid, _, _, _ = _project(client)
        company = client.get(f"/api/v1/applications/{aid}", headers=headers).json()["company_id"]
        response = client.post(
            "/api/v1/ask",
            headers=headers,
            json={"company_id": company, "question": "研发费用规则是什么"},
        )
        assert "保证获批" not in response.text and "[1]" in response.text
        assert (
            response.text.index("event: retrieval")
            < response.text.index("event: token")
            < response.text.index("event: citations")
            < response.text.index("event: done")
        )

        async def failure(*args, **kwargs):
            raise RuntimeError("synthetic provider failure")
            yield ""

        monkeypatch.setattr(workspace.gateway, "complete_stream", failure)
        cid = str(uuid.uuid4())
        response = client.post(
            "/api/v1/ask",
            headers=headers,
            json={"company_id": company, "question": "研发费用规则是什么", "request_id": cid},
        )
        assert "event: error" in response.text and "synthetic provider" not in response.text
        saved = client.get(f"/api/v1/workspace/conversations/{cid}", headers=headers).json()
        assert (
            saved["status"] == "failed" and saved["messages"][0]["content"] == "研发费用规则是什么"
        )


def test_disabled_feature_and_daily_limit(monkeypatch):
    with TestClient(app) as client:
        headers, _, aid, _, _, _ = _project(client)
        company = client.get(f"/api/v1/applications/{aid}", headers=headers).json()["company_id"]
        request = {"company_id": company, "question": "缺什么材料"}
        monkeypatch.setattr(settings, "workspace_ask_enabled", False)
        assert client.post("/api/v1/ask", headers=headers, json=request).status_code == 503
        monkeypatch.setattr(settings, "workspace_ask_enabled", True)
        monkeypatch.setattr(settings, "llm_daily_call_limit", 1)
        assert client.post("/api/v1/ask", headers=headers, json=request).status_code == 200
        assert client.post("/api/v1/ask", headers=headers, json=request).status_code == 429


def test_real_retrieval_filters_expiry_region_tenant_and_corrupt_snapshot(monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.models.models import Policy, PolicyVersion

    monkeypatch.setattr(settings, "workspace_ask_enabled", True)
    with TestClient(app) as client:
        headers, _, aid, _, _, policy_id = _project(client)
        foreign, _ = _register(client, uuid.uuid4().hex)
        company = client.get(f"/api/v1/applications/{aid}", headers=headers).json()["company_id"]
        foreign_company = client.get("/api/v1/companies", headers=foreign).json()[0]["id"]
        question = {"company_id": company, "question": "人工智能企业条件"}

        async def stream(*args, **kwargs):
            sources = json.loads(args[1][1]["content"])["sources"]
            quote = sources[0]["policy_quote"]
            yield json.dumps({"claims": [{"text": quote, "source": 1, "policy_quote": quote}]})

        monkeypatch.setattr(workspace.gateway, "complete_stream", stream)
        # A large corpus must not let higher-ranked but undated global records
        # consume all evidence slots before the valid private source is considered.
        with SessionLocal() as db:
            import hashlib

            from app.models.models import PolicyChunk
            text = "人工智能企业条件：此为日期未核实的合成样本。"
            for _ in range(12):
                distractor = Policy(title="人工智能企业条件", status="published", content=text)
                db.add(distractor)
                db.flush()
                version = PolicyVersion(policy_id=distractor.id, version=1,
                    title=distractor.title, content=text, status="published",
                    content_sha256=hashlib.sha256(text.encode()).hexdigest())
                db.add(version)
                db.flush()
                db.add(PolicyChunk(policy_id=distractor.id, policy_version_id=version.id,
                    chunk_index=0, content=text, char_start=0, char_end=len(text),
                    content_sha256=version.content_sha256))
            db.commit()
        response = client.post("/api/v1/ask", headers=headers, json=question)
        assert "[1]" in response.text and str(policy_id) in response.text
        foreign_response = client.post(
            "/api/v1/ask", headers=foreign, json={**question, "company_id": foreign_company}
        )
        assert str(policy_id) not in foreign_response.text
        with SessionLocal() as db:
            policy = db.get(Policy, policy_id)
            policy.expires_at = datetime.now(UTC) - timedelta(days=1)
            db.commit()
        expired = client.post("/api/v1/ask", headers=headers, json=question)
        assert str(policy_id) not in expired.text and "证据不足" in expired.text
        with SessionLocal() as db:
            policy = db.get(Policy, policy_id)
            policy.expires_at = datetime.now(UTC) + timedelta(days=90)
            policy.province = "浙江省"
            db.commit()
        assert str(policy_id) not in client.post("/api/v1/ask", headers=headers, json=question).text
        with SessionLocal() as db:
            policy = db.get(Policy, policy_id)
            policy.province = "上海市"
            version = db.scalar(select(PolicyVersion).where(PolicyVersion.policy_id == policy_id))
            version.content_sha256 = "0" * 64
            db.commit()
        assert str(policy_id) not in client.post("/api/v1/ask", headers=headers, json=question).text


def test_stream_fallback_before_first_delta_but_never_after_partial(monkeypatch):
    from app.services.llm import gateway as module
    from app.services.llm.budget import LLMLimitExceeded

    gateway = LLMGateway()
    monkeypatch.setattr(
        settings,
        "llm_task_routes",
        json.dumps(
            {
                "chat_answer": {
                    "primary": {"provider": "deepseek", "model": "synthetic"},
                    "fallback": {"provider": "qwen", "model": "synthetic"},
                    "stream": True,
                }
            }
        ),
    )
    monkeypatch.setattr(module, "reserve", lambda *args: (uuid.uuid4(), 100))
    settled = []
    monkeypatch.setattr(module, "settle", lambda *args: settled.append(args))
    calls = []

    class First:
        partial = False

        async def stream(self, request):
            calls.append("primary")
            if self.partial:
                yield {"token": "partial"}
            raise httpx.ReadTimeout("synthetic")

    class Second:
        async def stream(self, request):
            calls.append("fallback")
            yield {"token": "fallback"}

    first = First()
    gateway.providers["deepseek"] = first
    gateway.providers["qwen"] = Second()

    async def collect():
        return [token async for token in gateway.complete_stream(TaskType.chat_answer, [])]

    assert asyncio.run(collect()) == ["fallback"] and calls == ["primary", "fallback"]
    first.partial = True
    calls.clear()
    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(collect())
    assert calls == ["primary"]

    def denied(*args):
        raise LLMLimitExceeded("synthetic")

    monkeypatch.setattr(module, "reserve", denied)
    calls.clear()
    with pytest.raises(LLMLimitExceeded):
        asyncio.run(collect())
    assert not calls
