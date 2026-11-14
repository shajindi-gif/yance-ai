"""Park policy operations entry point.

Deliberately a sibling of ``scripts/policy_collection/cli.py`` rather than a new
service: the park layer reuses the existing catalogue, retrieval, permission and
task machinery, and must stay operable from the same shell.

Every command here works **without a database** except where explicitly noted, so
that coverage and evaluation stay inspectable during an outage or before a
migration is applied.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.park_policy import evaluation
from app.services.park_registry.catalog import (
    ParkCatalogError,
    find_parks,
    load_catalog,
)
from app.services.park_registry.geography import evaluate_scope


def cmd_parks_validate(args) -> int:
    try:
        catalog = load_catalog(args.catalog_dir)
    except ParkCatalogError as exc:
        print(f"园区目录校验失败: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK 园区目录 {catalog.catalog_version} "
        f"records={len(catalog.records)} files={len(catalog.source_files)} "
        f"digest={catalog.digest[:16]}"
    )
    return 0


def cmd_parks_summary(args) -> int:
    catalog = load_catalog(args.catalog_dir)
    from collections import Counter

    by_type = Counter(r.park_type for r in catalog.records)
    by_verification = Counter(r.verification_status for r in catalog.records)
    by_boundary = Counter(r.boundary_status for r in catalog.records)
    confirmed_boundaries = by_boundary.get("confirmed", 0)

    if args.json:
        print(
            json.dumps(
                {
                    "catalog_version": catalog.catalog_version,
                    "records": len(catalog.records),
                    "digest": catalog.digest,
                    "by_type": dict(by_type),
                    "by_verification": dict(by_verification),
                    "by_boundary": dict(by_boundary),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"catalog_version : {catalog.catalog_version}")
    print(f"records         : {len(catalog.records)}")
    print(f"digest          : {catalog.digest[:16]}")
    print(f"types           : {dict(by_type)}")
    print(f"verification    : {dict(by_verification)}")
    print(f"boundary        : {dict(by_boundary)}")
    if confirmed_boundaries == 0:
        print(
            "\n注意: 没有任何园区边界被核验为 confirmed，"
            "因此园区适用范围的判定结果一律为 needs_review（不是缺陷，是如实状态）。"
        )
    return 0


def cmd_parks_list(args) -> int:
    catalog = load_catalog(args.catalog_dir)
    records = find_parks(
        catalog,
        province=args.province,
        city=args.city,
        park_type=args.type,
    )
    for record in records:
        print(
            f"{record.park_id}\t{record.name}\t{record.park_type}\t"
            f"{record.province}/{record.city}\t{record.verification_status}\t"
            f"boundary={record.boundary_status}"
        )
    print(f"\n合计 {len(records)} 条", file=sys.stderr)
    return 0


def cmd_parks_scope(args) -> int:
    """Explain why a scope does or does not apply. Read-only, no DB, no inference."""
    catalog = load_catalog(args.catalog_dir)
    park = None
    if args.park_id:
        matches = [r for r in catalog.records if r.park_id == args.park_id]
        if not matches:
            print(f"未登记的园区 park_id={args.park_id}", file=sys.stderr)
            return 2
        park = matches[0]

    facts: dict[str, str] = {}
    for item in args.fact or []:
        if "=" not in item:
            print(f"事实格式应为 field=value，收到 {item!r}", file=sys.stderr)
            return 2
        key, value = item.split("=", 1)
        facts[key.strip()] = value.strip()

    scope = {
        "scope_type": args.level,
        "province": args.province_of_policy,
        "city": args.city_of_policy,
        "district": args.district_of_policy,
        "park_id": args.park_id,
        "requires_confirmation": not args.reviewed,
        "review_status": "confirmed" if args.reviewed else "needs_review",
        "qualification_basis": args.basis or "unspecified",
    }
    result = evaluate_scope(scope, facts, park=park)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, default=str))
    verdict = result.as_dict().get("verdict") or result.as_dict().get("status")
    print(f"\n结论: {verdict}", file=sys.stderr)
    return 0 if verdict == "satisfied" else 4


def cmd_eval_run(args) -> int:
    eval_set = evaluation.load_eval_set(args.eval_set)
    problems = evaluation.validate_eval_set(eval_set)
    if problems:
        for problem in problems:
            print(f"评测集问题: {problem}", file=sys.stderr)
        return 1

    report = evaluation.build_report(eval_set, model_name=args.model)
    if args.out:
        path = evaluation.write_report(report, args.out)
        print(f"报告已写入 {path}")

    print(f"eval_set   : {report['eval_set_version']} ({report['eval_set_digest']})")
    for arm in report["arms"]:
        status = "runnable" if arm["runnable"] else "blocked"
        print(f"\n[{arm['name']}] {status}")
        if not arm["runnable"]:
            print(f"  阻塞: {arm['blocked_reason']}")
            continue
        for suite, metrics in (arm["result"] or {}).get("by_suite", {}).items():
            print(
                f"  {suite}: tasks={metrics['tasks']} "
                f"behavior_match={metrics['behavior_match_rate']} "
                f"severe={metrics['severe_error_count']} "
                f"invented={metrics['invented_support_count']}"
            )
        blocked = (arm["result"] or {}).get("skipped_tasks") or []
        if blocked:
            print(f"  未评分: {len(blocked)} 题（缺材料，不以 0 分计）")

    floor = report["floor_arm"]["by_suite"]
    print("\n[过度声明基线]")
    for suite, metrics in floor.items():
        print(
            f"  {suite}: behavior_match={metrics['behavior_match_rate']} "
            f"severe={metrics['severe_error_rate']} "
            f"invented={metrics['invented_support_count']}"
        )

    print(f"\n业务质量结论: {report['conclusion']['business_quality']}")
    print(report["conclusion"]["statement"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="park policy & evidence operations")
    sub = parser.add_subparsers(dest="command", required=True)

    parks = sub.add_parser("parks", help="park catalogue operations (no DB)")
    parks_sub = parks.add_subparsers(dest="subcommand", required=True)

    p = parks_sub.add_parser("validate", help="validate the park catalogue")
    p.add_argument("--catalog-dir")
    p.set_defaults(func=cmd_parks_validate)

    p = parks_sub.add_parser("summary", help="counts by type/verification/boundary")
    p.add_argument("--catalog-dir")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_parks_summary)

    p = parks_sub.add_parser("list", help="list parks, optionally filtered")
    p.add_argument("--catalog-dir")
    p.add_argument("--province")
    p.add_argument("--city")
    p.add_argument("--type")
    p.set_defaults(func=cmd_parks_list)

    p = parks_sub.add_parser("scope", help="explain applicability for one case")
    p.add_argument("--catalog-dir")
    p.add_argument("--park-id", help="park scope 必填")
    p.add_argument("--level", required=True,
                   choices=["national", "province", "city", "district", "park"])
    p.add_argument("--province-of-policy")
    p.add_argument("--city-of-policy")
    p.add_argument("--district-of-policy")
    p.add_argument("--basis", help="园区归属依据: registration/tax/operation/statistics")
    p.add_argument("--reviewed", action="store_true",
                   help="该适用范围已与原文核对；缺省视为未核对，结论为需复核")
    p.add_argument("--fact", action="append", metavar="field=value")
    p.set_defaults(func=cmd_parks_scope)

    evaluate = sub.add_parser("eval", help="versioned comparison evaluation")
    eval_sub = evaluate.add_subparsers(dest="subcommand", required=True)
    p = eval_sub.add_parser("run", help="run every arm that is actually runnable")
    p.add_argument("--eval-set")
    p.add_argument("--model")
    p.add_argument("--out")
    p.set_defaults(func=cmd_eval_run)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"文件不存在: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
