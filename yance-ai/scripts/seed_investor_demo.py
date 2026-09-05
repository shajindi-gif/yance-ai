#!/usr/bin/env python3
"""Seed five public, synthetic demo workflows without users or commercial events."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal  # noqa: E402
from app.services.demo.scenarios import seed_investor_demo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace only tenants already marked is_demo with known dataset keys.",
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        scenarios = seed_investor_demo(db, replace=args.replace)
    print(f"Seeded {len(scenarios)} synthetic scenarios. No commerce or analytics rows created.")


if __name__ == "__main__":
    main()
