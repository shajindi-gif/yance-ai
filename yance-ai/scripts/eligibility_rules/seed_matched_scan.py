"""Seed exact-span rules for policies that actually appeared in a scan."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve()
for parent in _HERE.parents:
    if (parent / "app" / "core" / "db.py").exists():
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        break

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import EligibilityRule, Opportunity, Policy, PolicyChunk
from app.services.policies.rule_seeding import (
    build_candidates_for_policy,
    validate_candidate_against_version,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-id", required=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply
    scan_id = uuid.UUID(args.scan_id)

    created = 0
    skipped = 0
    no_cand = 0
    provinces: dict[str, int] = {}
    details: list[dict] = []

    with SessionLocal() as db:
        opps = list(db.scalars(select(Opportunity).where(Opportunity.scan_id == scan_id)).all())
        policy_ids: list = []
        for opp in opps:
            if not opp.policy_id:
                continue
            policy = db.get(Policy, opp.policy_id)
            if not policy:
                continue
            key = policy.province or "null"
            provinces[key] = provinces.get(key, 0) + 1
            policy_ids.append(policy.id)

        for policy_id in dict.fromkeys(policy_ids):
            policy = db.get(Policy, policy_id)
            assert policy is not None
            version, candidates = build_candidates_for_policy(db, policy)
            if version is None or not candidates:
                no_cand += 1
                details.append(
                    {
                        "policy_id": str(policy_id),
                        "title": (policy.title or "")[:70],
                        "status": "no_candidates",
                        "province": policy.province,
                    }
                )
                continue
            chunk_texts = [
                chunk.content or ""
                for chunk in db.scalars(
                    select(PolicyChunk).where(PolicyChunk.policy_version_id == version.id)
                ).all()
            ]
            made = 0
            for candidate in candidates:
                error = validate_candidate_against_version(
                    content=version.content or "",
                    chunk_texts=chunk_texts,
                    candidate=candidate,
                )
                if error:
                    continue
                existing = db.scalar(
                    select(EligibilityRule).where(
                        EligibilityRule.policy_version_id == version.id,
                        EligibilityRule.fact_key == candidate.fact_key,
                        EligibilityRule.source_quote == candidate.source_quote,
                        EligibilityRule.status == "active",
                    )
                )
                if existing:
                    skipped += 1
                    continue
                if dry_run:
                    created += 1
                    made += 1
                    continue
                db.add(
                    EligibilityRule(
                        policy_id=policy.id,
                        policy_version_id=version.id,
                        tenant_id=None,
                        name=candidate.name,
                        fact_key=candidate.fact_key,
                        operator=candidate.operator,
                        expected_json=candidate.expected_json,
                        is_hard_gate=True,
                        source_quote=candidate.source_quote,
                        status="active",
                    )
                )
                created += 1
                made += 1
            details.append(
                {
                    "policy_id": str(policy_id),
                    "title": (policy.title or "")[:70],
                    "status": "seeded" if made else "skipped",
                    "candidates": made,
                    "province": policy.province,
                }
            )
        if not dry_run:
            db.commit()

    print(
        json.dumps(
            {
                "scan_id": str(scan_id),
                "dry_run": dry_run,
                "created_or_would_create": created,
                "skipped_existing": skipped,
                "no_candidates": no_cand,
                "province_histogram": provinces,
                "details": details,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
