"""Import crawler JSONL into the policy knowledge base.

Each item goes through: deterministic funding-amount parsing → Policy row
(global knowledge base) → version_and_chunk_policy (chunks + embeddings).
Import is idempotent on source_url (skip already-imported policies).

Usage (server or local with DB access):
    python -m scripts.policy_crawler.import_jsonl crawler_output/policies.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.models import Policy
from app.services.funding.amounts import infer_funding_type, parse_support_amount
from app.services.policies.ingestion import version_and_chunk_policy


def import_item(db: Session, item: dict) -> str:
    """Create or update one policy from a crawler item. Returns action taken."""
    existing = db.scalar(select(Policy).where(Policy.source_url == item["source_url"]))
    if existing:
        return "skipped_existing"

    parsed = parse_support_amount(item.get("support_amount_hint"))
    support_amount = item.get("support_amount_hint")
    if not support_amount and parsed.parsed:
        if parsed.amount_max is not None:
            support_amount = f"最高{parsed.amount_max:g}万"
        elif parsed.amount_min is not None:
            support_amount = f"{parsed.amount_min:g}万"

    policy = Policy(
        tenant_id=None,  # global knowledge base
        title=item["title"],
        issuing_authority=item.get("issuing_authority"),
        level=item.get("level"),
        province=item.get("province"),
        city=item.get("city"),
        policy_type="subsidy" if (parsed.parsed and parsed.amount_max) else None,
        source_url=item.get("source_url"),
        jurisdiction=f"{item.get('province', '')}{item.get('city', '')}".strip("上海北京市") or None,
        published_at=_parse_dt(item.get("published_at")),
        support_amount=support_amount,
        support_type=None,
        funding_type=infer_funding_type(support_amount, None),
        funding_amount_min=parsed.amount_min,
        funding_amount_max=parsed.amount_max,
        funding_ratio=parsed.ratio,
        funding_currency="CNY",
        content=item.get("content", "")[:100_000],
        original_text=None,
        source=item.get("source_key"),
        crawled_at=_parse_dt(item.get("crawled_at")),
        status="published",
    )
    db.add(policy)
    db.flush()
    version_and_chunk_policy(db, policy)  # chunks + embedding + immutable version
    return "imported"


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        from datetime import datetime

        return datetime.fromisoformat(value)
    except ValueError:
        return None


def main(path: str) -> None:
    items = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    imported = skipped = failed = 0
    with SessionLocal() as db:
        for item in items:
            try:
                action = import_item(db, item)
                if action == "imported":
                    imported += 1
                else:
                    skipped += 1
            except Exception as exc:
                failed += 1
                print(f"  failed: {item.get('title', '?')[:40]} -> {exc}")
        db.commit()
    print(f"import done: imported={imported} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "crawler_output/policies.jsonl")
