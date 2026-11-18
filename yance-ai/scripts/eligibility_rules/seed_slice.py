#!/usr/bin/env python3
"""Seed exact-span EligibilityRules for a geographic slice.

Examples:
  python -m scripts.eligibility_rules.seed_slice --province 上海市 --limit 40 --dry-run
  python -m scripts.eligibility_rules.seed_slice --province 上海市 --limit 40 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# When launched as a repo script, put the backend root on sys.path. In the API
# image the `app` package is already importable and this is a no-op.
_HERE = Path(__file__).resolve()
for parent in _HERE.parents:
    if (parent / "app" / "core" / "db.py").exists():
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        break

from app.core.db import SessionLocal  # noqa: E402
from app.services.policies.rule_seeding import coverage_metrics, seed_rules_for_slice  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--province", default="上海市")
    parser.add_argument(
        "--national-topics",
        action="store_true",
        help="Ignore province filter; seed topic keywords across published corpus",
    )
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="Persist rules (disables dry-run)")
    parser.add_argument("--metrics-only", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    dry_run = not args.apply
    province = None if args.national_topics else args.province

    with SessionLocal() as db:
        if args.metrics_only:
            payload = coverage_metrics(db, province=args.province)
        else:
            payload = seed_rules_for_slice(
                db,
                province=province,
                limit=args.limit,
                dry_run=dry_run,
                tenant_id=None,
            )
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
