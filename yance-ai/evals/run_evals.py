"""Validate or execute the canonical five-part Yance evaluation bundle."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import Tenant, User
from app.services.evaluations.contracts import EVAL_TYPES
from app.services.evaluations.loader import load_dataset
from app.services.evaluations.runner import execute_bundle, persist_executions


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("evals/datasets"))
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("validate")
    run = subcommands.add_parser("run")
    run.add_argument("--eval-type", choices=["all", *EVAL_TYPES], default="all")
    run.add_argument("--no-persist", action="store_true")
    run.add_argument("--tenant-slug")
    run.add_argument("--email")
    return parser


def _summary(executions) -> dict:
    return {
        "datasets": len(executions),
        "requested_cases": sum(item.requested_cases for item in executions),
        "completed_cases": sum(item.completed_cases for item in executions),
        "passed_cases": sum(item.passed_cases for item in executions),
        "error_cases": sum(item.error_cases for item in executions),
        "release_gate_passed": bool(executions)
        and all(item.release_gate_passed for item in executions),
        "runs": [
            {
                "eval_type": item.dataset.eval_type,
                "dataset": item.dataset.key,
                "version": item.dataset.version,
                "review_status": item.dataset.review_status,
                "data_classification": item.dataset.data_classification,
                "target": f"{item.dataset.target_key}@{item.dataset.target_version}",
                "scorer": item.dataset.scorer_version,
                "requested": item.requested_cases,
                "passed": item.passed_cases,
                "errors": item.error_cases,
                "release_gate_passed": item.release_gate_passed,
            }
            for item in executions
        ],
    }


def main() -> int:
    args = _parser().parse_args()
    if args.command == "validate":
        datasets = [load_dataset(args.root, eval_type) for eval_type in EVAL_TYPES]
        print(
            json.dumps(
                {
                    "datasets": len(datasets),
                    "cases": sum(len(item.cases) for item in datasets),
                    "valid": True,
                    "review_statuses": sorted({item.card.review_status for item in datasets}),
                },
                ensure_ascii=False,
            )
        )
        return 0

    selected = list(EVAL_TYPES) if args.eval_type == "all" else [args.eval_type]
    executions = execute_bundle(args.root, selected)
    summary = _summary(executions)
    if not args.no_persist:
        if not args.tenant_slug or not args.email:
            raise SystemExit("persisted runs require --tenant-slug and --email")
        with SessionLocal() as db:
            user = db.scalar(
                select(User)
                .join(Tenant, Tenant.id == User.tenant_id)
                .where(
                    User.email == args.email.lower(),
                    Tenant.slug == args.tenant_slug,
                    User.is_platform_admin.is_(True),
                )
            )
            if not user:
                raise SystemExit("exact platform administrator and tenant match not found")
            runs = persist_executions(
                db,
                executions,
                tenant_id=user.tenant_id,
                user_id=user.id,
            )
            summary["persisted_run_ids"] = [str(run.id) for run in runs]
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["release_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
