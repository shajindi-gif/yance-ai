#!/usr/bin/env python3
"""Backfill Policy date fields from version columns or explicit text spans only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
for parent in _HERE.parents:
    if (parent / "app" / "core" / "db.py").exists():
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        break

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import EligibilityRule, Policy, PolicyVersion
from app.services.policies.policy_dates import merge_dates_for_policy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--ruled-only", action="store_true", default=True)
    parser.add_argument("--all-published", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply
    ruled_only = not args.all_published

    updated = 0
    scanned = 0
    samples: list[dict] = []
    with SessionLocal() as db:
        if ruled_only:
            policy_ids = list(
                db.scalars(
                    select(EligibilityRule.policy_id).where(EligibilityRule.status == "active").distinct()
                ).all()
            )
            policies = list(db.scalars(select(Policy).where(Policy.id.in_(policy_ids))).all()) if policy_ids else []
        else:
            policies = list(
                db.scalars(
                    select(Policy).where(Policy.status == "published").limit(args.limit)
                ).all()
            )
        for policy in policies[: args.limit]:
            scanned += 1
            version = db.scalar(
                select(PolicyVersion)
                .where(PolicyVersion.policy_id == policy.id, PolicyVersion.status == "published")
                .order_by(PolicyVersion.version.desc())
            )
            content = (version.content if version else None) or policy.content or ""
            merged = merge_dates_for_policy(policy=policy, version=version, content=content)
            updates = merged["updates"]
            if not updates:
                continue
            if dry_run:
                updated += 1
            else:
                for key, value in updates.items():
                    setattr(policy, key, value)
                updated += 1
            if len(samples) < 20:
                samples.append(
                    {
                        "policy_id": str(policy.id),
                        "title": (policy.title or "")[:70],
                        "updates": {k: str(v) for k, v in updates.items()},
                        "evidence": merged["evidence"],
                    }
                )
        if not dry_run:
            db.commit()
    print(
        json.dumps(
            {
                "dry_run": dry_run,
                "scanned": scanned,
                "updated_or_would_update": updated,
                "samples": samples,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
