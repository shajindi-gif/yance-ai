#!/usr/bin/env python
"""Operational entry point for the continuous policy collection system.

Usage (run from ``yance-ai/``)::

    ./.venv/bin/python scripts/policy_collection/cli.py validate
    ./.venv/bin/python scripts/policy_collection/cli.py coverage --markdown
    ./.venv/bin/python scripts/policy_collection/cli.py verify --level national
    ./.venv/bin/python scripts/policy_collection/cli.py run --source national_gov_policy --dry-run
    ./.venv/bin/python scripts/policy_collection/cli.py run-due --limit 5
    ./.venv/bin/python scripts/policy_collection/cli.py status
    ./.venv/bin/python scripts/policy_collection/cli.py pause mof_gov_cn_policy
    ./.venv/bin/python scripts/policy_collection/cli.py resume mof_gov_cn_policy
    ./.venv/bin/python scripts/policy_collection/cli.py retry mof_gov_cn_policy --max-items 3

Commands split in two groups on purpose:

* catalog-only (``validate``, ``plan``, ``verify``) need **no database** and are
  safe to run anywhere, including a dry box with no Postgres.
* database commands report a clear message when the database is unreachable
  instead of failing with a stack trace.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.policy_collection.adapters import (  # noqa: E402
    ListUnavailable,
    resolve_adapter,
)
from app.services.policy_collection.catalog import load_catalog  # noqa: E402
from app.services.policy_collection.fetch import SafeFetcher  # noqa: E402
from app.services.policy_collection.runner import CollectionLimits  # noqa: E402
from app.services.policy_collection.urlguard import TargetPolicy  # noqa: E402

CATALOG_DIR = settings.policy_collection_catalog_dir


def _catalog():
    return load_catalog(CATALOG_DIR)


def _session():
    from app.core.db import SessionLocal

    return SessionLocal()


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.astimezone().strftime("%Y-%m-%d %H:%M")
    return str(value)


def cmd_validate(args) -> int:
    catalog = _catalog()
    problems = catalog.validate()
    stats = catalog.coverage()
    print(f"catalog: {CATALOG_DIR}")
    print(f"sources: {len(catalog.sources)}  cities: {len(catalog.cities)}")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nvalidate: OK")
    return 0


def cmd_plan(args) -> int:
    catalog = _catalog()
    groups: dict[str, list] = {}
    for source in catalog.sources:
        groups.setdefault(source.level, []).append(source)
    for level in ("national", "provincial", "municipal"):
        items = groups.get(level, [])
        enabled = [s for s in items if s.enabled]
        print(f"{level}: {len(items)} registered, {len(enabled)} enabled")
        for source in items[: args.limit]:
            flag = "on " if source.enabled else "off"
            print(
                f"  [{flag}] {source.source_id:<34} {source.verification_state:<16}"
                f" {source.check_interval_hours:>5}h  {source.name}"
            )
    cities = sorted({s.city for s in catalog.sources if s.level == "municipal" and s.city})
    print(f"\npriority cities with sources: {len(cities)}/{len(catalog.cities)}")
    return 0


def cmd_verify(args) -> int:
    """Read-only reachability check: one GET per source list page, no writes."""
    catalog = _catalog()
    targets = [s for s in catalog.sources if s.enabled]
    if args.source:
        wanted = [item.strip() for item in str(args.source).split(",") if item.strip()]
        targets = [s for s in targets if s.source_id in wanted]
    if args.level:
        targets = [s for s in targets if s.level == args.level]
    if args.limit:
        targets = targets[: args.limit]
    limits = CollectionLimits.from_settings(settings)
    print(f"verifying {len(targets)} source(s); read-only, 1 request each\n")
    ok = fail = 0
    for source in targets:
        fetcher = SafeFetcher(
            target_policy=TargetPolicy(
                allowed_domains=tuple(source.allowed_domains) or (source.entry_host,),
                allowed_ports=tuple({80, 443, *source.allow_non_standard_ports}),
            ),
            user_agent=settings.policy_collection_user_agent,
            max_bytes=limits.max_detail_bytes,
            timeout_seconds=limits.request_timeout_seconds,
            min_interval_seconds=limits.min_host_interval_seconds,
            max_retries=1,
            respect_robots=limits.respect_robots,
        )
        # Verify through the real adapter path so client-side redirect shells,
        # JPAAS columns and pagination behave exactly as they do in a live run.
        adapter = resolve_adapter(source)
        try:
            fetched = adapter.fetch(fetcher, source, max_pages=1)
        except ListUnavailable as exc:
            result = exc.result
            if result is None:
                fail += 1
                print(f"FAIL {source.source_id:<34} kind=adapter {exc}")
                continue
        else:
            ok += 1
            note = f" ({fetched.note})" if fetched.note else ""
            print(
                f"OK   {source.source_id:<34} http=200 "
                f"entries={len(fetched.entries):<3} {fetched.adapter_used}{note}"
            )
            continue
        if result.ok:
            ok += 1
            print(
                f"OK   {source.source_id:<34} http={result.status_code} "
                f"entries=0   {result.elapsed_ms}ms"
            )
        else:
            fail += 1
            kind = "robots" if result.robots_denied else (result.error_kind or "http")
            print(
                f"FAIL {source.source_id:<34} kind={kind} "
                f"http={result.status_code} {result.error or ''}"
            )
    print(f"\nverified: {ok} ok, {fail} failed")
    return 0 if fail == 0 else 1


def cmd_run(args) -> int:
    from app.services.policy_collection.service import execute_source_run

    catalog = _catalog()
    if args.source:
        matches = [s for s in catalog.sources if s.source_id == args.source]
        if not matches:
            print(f"unknown source_id: {args.source}")
            return 2
        targets = matches
    else:
        targets = [s for s in catalog.sources if s.enabled]
        if args.level:
            targets = [s for s in targets if s.level == args.level]
        if args.limit:
            targets = targets[: args.limit]
    if not targets:
        print("no enabled source matched")
        return 2

    if args.dry_run:
        # No database, no writes to the policy tables: proves the pipeline end to end.
        for source in targets:
            report = execute_source_run(
                None, source, trigger="manual", max_items=args.max_items, dry_run=True
            )
            outcome = report.outcome
            print(
                f"[dry-run] {source.source_id} status={report.status} "
                f"pages={outcome.pages_fetched} entries={outcome.list_entries} "
                f"new={outcome.new_documents} updated={outcome.updated_documents} "
                f"unchanged={outcome.unchanged_documents} failed={outcome.failed_documents} "
                f"attachments={outcome.attachments_saved}/{outcome.attachments_failed} "
                f"{outcome.duration_ms}ms"
            )
            for item in outcome.items[: args.limit or 5]:
                print(f"    - {item.status:<13} {item.title[:44]:<46} {item.url[:70]}")
            if outcome.error:
                print(f"    ! {outcome.error_kind}: {outcome.error}")
        return 0

    session = _session()
    try:
        exit_code = 0
        for source in targets:
            report = execute_source_run(
                session,
                source,
                trigger=args.trigger,
                max_items=args.max_items,
            )
            if report.skipped_reason:
                print(f"[skip] {source.source_id}: {report.skipped_reason}")
                continue
            outcome = report.outcome
            print(
                f"[run ] {source.source_id} status={report.status} run={report.run_id} "
                f"new={outcome.new_documents} updated={outcome.updated_documents} "
                f"unchanged={outcome.unchanged_documents} failed={outcome.failed_documents}"
            )
            if outcome.error:
                print(f"       ! {outcome.error_kind}: {outcome.error}")
                exit_code = 1
        return exit_code
    finally:
        session.close()


def cmd_run_due(args) -> int:
    from app.services.policy_collection.service import due_sources, execute_source_run

    catalog = _catalog()
    session = _session()
    try:
        due = due_sources(catalog, session)
        if args.limit:
            due = due[: args.limit]
        print(f"due sources: {len(due)}")
        for source in due:
            report = execute_source_run(session, source, trigger="cron")
            if report.skipped_reason:
                print(f"  [skip] {source.source_id}: {report.skipped_reason}")
                continue
            outcome = report.outcome
            print(
                f"  [{report.status}] {source.source_id} new={outcome.new_documents} "
                f"updated={outcome.updated_documents} failed={outcome.failed_documents}"
            )
        return 0
    finally:
        session.close()


def cmd_coverage(args) -> int:
    from app.services.policy_collection.service import coverage_rows

    catalog = _catalog()
    session = _session()
    try:
        rows = coverage_rows(catalog, session)
    finally:
        session.close()
    if args.level:
        rows = [r for r in rows if r["level"] == args.level]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        return 0
    if args.markdown:
        stage_counts: dict[str, int] = {}
        level_counts: dict[str, int] = {}
        for row in rows:
            stage_counts[row["stage"]] = stage_counts.get(row["stage"], 0) + 1
            level_counts[row["level"]] = level_counts.get(row["level"], 0) + 1
        stages = (
            "registered",
            "reachable",
            "fetched",
            "parsed",
            "searchable",
            "in_production",
        )
        print("### 阶段分布\n")
        print("| 阶段 | 来源数 | 含义 |")
        print("| --- | --- | --- |")
        meaning = {
            "registered": "已登记（仅目录，未验证）",
            "reachable": "已连通（入口可访问）",
            "fetched": "已采到原文（正文入库）",
            "parsed": "已解析（字段/附件解析）",
            "searchable": "已进入可用检索",
            "in_production": "已生产运行（按计划持续采集）",
        }
        for stage in stages:
            print(f"| {stage} | {stage_counts.get(stage, 0)} | {meaning[stage]} |")
        print(f"| 合计 | {len(rows)} | |")
        print("\n### 层级分布\n")
        print("| 层级 | 来源数 |")
        print("| --- | --- |")
        for level in ("national", "provincial", "municipal"):
            print(f"| {level} | {level_counts.get(level, 0)} |")
        print("\n### 逐来源明细\n")
        print("| source_id | 层级 | 地区 | 阶段 | 文档 | 已解析 | 可检索 | 最近成功 |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for row in rows:
            area = row["province"] or "-"
            if row["city"]:
                area = f"{row['province'] or ''}{row['city']}"
            print(
                f"| `{row['source_id']}` | {row['level']} | {area} | {row['stage']} | "
                f"{row['documents']} | {row['parsed']} | {row['searchable_documents']} | "
                f"{_fmt(row['last_success_at'])} |"
            )
        return 0
    for row in rows:
        area = f"{row['province'] or ''}{row['city'] or ''}"
        print(
            f"{row['stage']:<13} {row['source_id']:<34} {row['level']:<10} {area:<8} "
            f"docs={row['documents']:<4} searchable={row['searchable_documents']:<4} "
            f"last_ok={_fmt(row['last_success_at'])} err={_fmt(row['last_error_kind'])}"
        )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["stage"]] = counts.get(row["stage"], 0) + 1
    print("\nstage summary:", json.dumps(counts, ensure_ascii=False))
    return 0


def cmd_status(args) -> int:
    from app.services.policy_collection.service import health_report

    catalog = _catalog()
    session = _session()
    try:
        health = health_report(session)
    finally:
        session.close()
    print(f"catalog sources: {len(catalog.sources)}  enabled: {catalog.coverage()['sources_enabled']}")
    print(f"evidence on disk: {health['evidence_mb']} MB")
    print(
        f"attachments: {health['attachments']} (failed {health['attachments_failed']})  "
        f"versions: {health['versions']}  chunks: {health['chunks']}  "
        f"parsed-without-chunks: {health['policies_pending_review']}"
    )
    print("\nrecent runs:")
    for run in health["recent_runs"]:
        print(
            f"  {_fmt(run['started_at'])} {run['source_id']:<32} {run['status']:<10} "
            f"new={run['new']} changed={run['changed']} failed={run['failed']} "
            f"err={_fmt(run['error_kind'])}"
        )
    return 0


def cmd_pause(args) -> int:
    from app.services.policy_collection.service import pause_source

    session = _session()
    try:
        state = pause_source(session, args.source, reason=args.reason or "manual")
        print(f"paused {state.source_id}: {state.paused_reason}")
        print("already-collected policies stay readable; only scheduling stops.")
        return 0
    finally:
        session.close()


def cmd_resume(args) -> int:
    from app.services.policy_collection.service import resume_source

    session = _session()
    try:
        state = resume_source(session, args.source)
        print(f"resumed {state.source_id} (failures reset)")
        return 0
    finally:
        session.close()


def cmd_retry(args) -> int:
    args.trigger = "retry"
    return cmd_run(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="policy collection operations")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate the source catalog (no DB)")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("plan", help="show registered sources by level (no DB)")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("verify", help="read-only reachability check (no DB, no writes)")
    p.add_argument("--source")
    p.add_argument("--level", choices=["national", "provincial", "municipal"])
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_verify)

    for name, func in (("run", cmd_run), ("retry", cmd_retry)):
        p = sub.add_parser(name, help="collect one or more sources")
        p.add_argument("--source")
        p.add_argument("--level", choices=["national", "provincial", "municipal"])
        p.add_argument("--limit", type=int)
        p.add_argument("--max-items", type=int)
        p.add_argument("--dry-run", action="store_true", help="no database, no writes")
        p.add_argument("--trigger", default="manual")
        p.set_defaults(func=func)

    p = sub.add_parser("run-due", help="run every source whose interval elapsed")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_run_due)

    p = sub.add_parser("coverage", help="six-state coverage matrix")
    p.add_argument("--level", choices=["national", "provincial", "municipal"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    p.set_defaults(func=cmd_coverage)

    p = sub.add_parser("status", help="health, backlog and recent runs")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("pause", help="stop scheduling a source (reads unaffected)")
    p.add_argument("source")
    p.add_argument("--reason")
    p.set_defaults(func=cmd_pause)

    p = sub.add_parser("resume", help="resume a paused source")
    p.add_argument("source")
    p.set_defaults(func=cmd_resume)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # database-less environment: explain, don't traceback
        name = type(exc).__name__
        if name in {"OperationalError", "InterfaceError", "ProgrammingError"}:
            print(
                "database unavailable: this command needs PostgreSQL with the "
                "policy collection migration applied.\n"
                f"  detail: {exc}",
                file=sys.stderr,
            )
            print(
                "  no-database alternatives: validate / plan / verify / run --dry-run",
                file=sys.stderr,
            )
            return 3
        raise


if __name__ == "__main__":
    raise SystemExit(main())
