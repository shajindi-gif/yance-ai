"""Model-cost accounting for the collection pipeline.

The governed position for this phase is: **no paid model calls until a budget is
approved**.  This module therefore answers three questions without ever making a
call of its own:

1. how much embedding work is queued (and would be billable),
2. what the configured budget is,
3. how much of it has actually been consumed.

Consumption is reported as "unmetered" when no usage meter exists for the
collection pipeline.  Saying "0 calls" would be a lie if someone later enables
embeddings outside this module, so ``calls_today`` carries an explicit
``metered`` flag that the CLI surfaces.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Rough characters-per-token ratio used for a *pre-quote* only.  The real number
# comes from the provider's response once calls are enabled.
CHARS_PER_TOKEN = 1.6


def _setting(name: str, default=None):
    return getattr(settings, name, default)


def pending_embedding_work(db: Session, *, limit_rows: int = 200_000) -> dict:
    """Count documents/chunks that still need a vector, with a token estimate."""
    try:
        chunks = db.execute(
            text(
                """
                SELECT COUNT(*) AS n, COALESCE(SUM(LENGTH(c.content)), 0) AS chars
                FROM policy_chunks c
                JOIN policies p ON p.id = c.policy_id
                WHERE c.embedding IS NULL AND p.status = 'published'
                LIMIT :cap
                """
            ),
            {"cap": limit_rows},
        ).one()
        policies = db.execute(
            text(
                """
                SELECT COUNT(*) AS n, COALESCE(SUM(LENGTH(p.content)), 0) AS chars
                FROM policies p
                WHERE p.embedding IS NULL AND p.status = 'published'
                """
            )
        ).one()
        done = db.execute(
            text("SELECT COUNT(*) FROM policy_chunks WHERE embedding IS NOT NULL")
        ).scalar()
    except Exception as exc:  # pragma: no cover - reported, never fatal
        logger.warning("embedding backlog unavailable: %s", exc)
        return {"available": False, "error": str(exc)}

    chunk_chars = int(chunks.chars or 0)
    policy_chars = int(policies.chars or 0)
    total_chars = chunk_chars + policy_chars
    return {
        "available": True,
        "pending_chunks": int(chunks.n or 0),
        "pending_policies": int(policies.n or 0),
        "embedded_chunks": int(done or 0),
        "pending_chars": total_chars,
        "estimated_tokens": int(total_chars / CHARS_PER_TOKEN),
        "chars_per_token_assumption": CHARS_PER_TOKEN,
    }


def cost_report(db: Session) -> dict:
    """Budget, backlog and honest consumption status (never guesses spend)."""
    budget_calls = int(_setting("policy_collection_daily_model_budget_calls", 0) or 0)
    embedding_model = _setting("embedding_model", None)
    dimension = _setting("embedding_dimension", None) or 1024

    work = pending_embedding_work(db)

    calls_today = 0
    metered = False
    meter_note = "no usage meter is wired for the collection pipeline"
    try:
        row = db.execute(
            text(
                """
                SELECT COUNT(*) FROM policy_raw_evidence
                WHERE created_at >= :since
                """
            ),
            {"since": datetime.now(UTC) - timedelta(days=1)},
        ).scalar()
        evidence_24h = int(row or 0)
    except Exception:  # pragma: no cover
        evidence_24h = 0

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "budget": {
            "daily_calls_limit": budget_calls,
            "remaining_calls_today": max(0, budget_calls - calls_today) if metered else budget_calls,
            "enabled": budget_calls > 0,
        },
        "consumption": {
            "calls_today": calls_today,
            "metered": metered,
            "note": meter_note,
            "evidence_rows_24h": evidence_24h,
        },
        "embedding": {
            "model": embedding_model,
            "dimension": dimension,
            "vectorisation_enabled": budget_calls > 0,
            "backlog": work,
            "currency_note": (
                "unit price is not configured; supply it before enabling paid calls "
                "so cost can be quoted rather than estimated"
            ),
        },
        "policy": (
            "原文采集、确定性解析、结构化入库与关键词检索均不调用模型；"
            "向量化在预算确认前保持关闭。"
        ),
    }
