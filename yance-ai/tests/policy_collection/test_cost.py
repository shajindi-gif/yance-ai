"""Cost reporting must never round "unknown" up to "zero spend"."""

from __future__ import annotations

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.policy_collection.cost import cost_report, pending_embedding_work


def test_cost_report_declares_unmetered_consumption(monkeypatch):
    monkeypatch.setattr(settings, "policy_collection_daily_model_budget_calls", 0, raising=False)
    with SessionLocal() as db:
        payload = cost_report(db)

    assert payload["budget"]["daily_calls_limit"] == 0
    assert payload["budget"]["enabled"] is False
    assert payload["embedding"]["vectorisation_enabled"] is False
    # The honest bit: no meter means spend is unknown, not zero.
    assert payload["consumption"]["metered"] is False
    assert "no usage meter" in payload["consumption"]["note"]
    assert "预算确认前保持关闭" in payload["policy"]


def test_embedding_backlog_is_counted_separately_from_search():
    with SessionLocal() as db:
        backlog = pending_embedding_work(db)

    assert backlog["available"] is True
    assert backlog["pending_chars"] >= 0
    # A token estimate must be labelled as an assumption, never quoted as fact.
    assert backlog["chars_per_token_assumption"] > 0
