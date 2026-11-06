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
    ./.venv/bin/python scripts/policy_collection/cli.py backfill-plan --max-sources 5
    ./.venv/bin/python scripts/policy_collection/cli.py backfill-run --max-sources 3 --docs 15
    ./.venv/bin/python scripts/policy_collection/cli.py backfill-status
    ./.venv/bin/python scripts/policy_collection/cli.py backlog
    ./.venv/bin/python scripts/policy_collection/cli.py heartbeat

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


def _backfill_config(args):
    from app.services.policy_collection.backfill import BackfillConfig

    source_ids = tuple(part.strip() for part in (args.sources or "").split(",") if part.strip())
    return BackfillConfig.from_settings(
        max_sources=getattr(args, "max_sources", None),
        pages_per_batch=getattr(args, "pages", None),
        docs_per_batch=getattr(args, "docs", None),
        seconds_budget=getattr(args, "seconds", None),
        source_ids=source_ids,
    )


def cmd_backfill_plan(args) -> int:
    from app.services.policy_collection.backfill import plan

    catalog = _catalog()
    session = _session()
    try:
        rows = plan(session, catalog, config=_backfill_config(args))
    finally:
        session.close()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        return 0
    print(f"backfill plan: {len(rows)} source(s)")
    for row in rows:
        flags = []
        if row.get("exhausted"):
            flags.append("exhausted")
        if row.get("unsupported_reason"):
            flags.append(f"unsupported:{row['unsupported_reason']}")
        print(
            f"  {row['source_id']:<32} {row['level']:<10} {row['channel']:<10} "
            f"next_page={row.get('next_page', 1):<3} {' '.join(flags)}"
        )
    return 0


def cmd_backfill_run(args) -> int:
    from app.services.policy_collection.backfill import run_batch

    # The collector is off by default so nothing downloads pages by accident.  A
    # backfill batch therefore needs the operator to say so on the command line;
    # the flag is per-process and never persists a config change.
    if args.enable_collection:
        settings.policy_collection_enabled = True
    elif not settings.policy_collection_enabled:
        print(
            "collection is disabled (POLICY_COLLECTION_ENABLED=false).\n"
            "  pass --enable-collection to run this batch explicitly, or enable it for "
            "a managed worker deliberately.",
            file=sys.stderr,
        )
        return 4

    catalog = _catalog()
    session = _session()
    code = 0
    try:
        report = run_batch(session, catalog, config=_backfill_config(args), dry_run=args.dry_run)
    finally:
        session.close()
    if args.json:
        print(json.dumps(report.as_dict() if hasattr(report, "as_dict") else report.__dict__,
                         ensure_ascii=False, indent=2, default=str))
        return code
    print(f"backfill batch {report.started_at} -> {report.finished_at} stop={_fmt(report.stop_reason)}")
    if report.storage:
        print(f"  disk: free={report.storage.get('free_mb')}MB ok={report.storage.get('ok')}")
    for result in report.sources:
        print(
            f"  [{result.status}] {result.source_id:<32} pages {result.page_from}-{result.page_to} "
            f"read={result.pages_read} new={result.documents_new} changed={result.documents_changed} "
            f"unchanged={result.documents_unchanged} failed={result.documents_failed} "
            f"stop={_fmt(result.stop_reason)}"
        )
        if result.status == "failed":
            code = 1
    for skipped in report.skipped:
        print(f"  [skip] {skipped['source_id']}: {skipped['reason']} {skipped.get('detail') or ''}".rstrip())
    if report.stop_reason in {"storage_full", "paused"}:
        print(f"batch stopped early: {report.stop_reason} (no cursor was advanced past it)")
        code = 2
    return code


def cmd_backfill_status(args) -> int:
    from app.services.policy_collection.backfill import status

    catalog = _catalog()
    session = _session()
    try:
        payload = status(session, catalog)
    finally:
        session.close()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    print(
        f"backfill: enabled={payload['enabled_sources']} pending={payload['pending']} "
        f"exhausted={payload['exhausted']} unsupported={payload['unsupported']}"
    )
    for row in payload["sources"]:
        flags = []
        if row["exhausted"]:
            flags.append("exhausted")
        if row["unsupported_reason"]:
            flags.append(f"unsupported:{row['unsupported_reason']}")
        if row["paused"]:
            flags.append("paused")
        print(
            f"  {row['source_id']:<32} page={row['page']:<3} stored={row['documents_stored']:<5} "
            f"{' '.join(flags)}"
        )
    return 0


def cmd_backfill_reset(args) -> int:
    """Clear a parked or stuck backfill cursor so the source is re-read.

    Two situations need this and neither should require hand-editing the database:

    * a cursor was parked after repeated empty pages (``backfill_blocked``) and the
      list rule has since been fixed;
    * an operator wants to re-read the archive window from a specific page after a
      site reorganisation.

    History is never deleted here: the cursor moves, the collected documents and
    their raw evidence stay exactly where they are.
    """
    from app.models.policy_collection import PolicySourceState
    from app.services.policy_collection.backfill import CURSOR_KEY, read_cursor, write_cursor

    session = _session()
    try:
        state = session.query(PolicySourceState).filter_by(source_id=args.source).one_or_none()
        if state is None:
            print(f"no cursor state for source_id: {args.source}")
            return 2
        cursor = read_cursor(state)
        cleared = [key for key in ("backfill_blocked", "gap_reason", "gap_page", "unsupported_reason") if key in cursor]
        for key in cleared:
            cursor.pop(key, None)
        cursor["gap_streak"] = 0
        if args.page:
            cursor["page"] = max(1, args.page)
            cursor["exhausted"] = False
        if args.exhausted:
            cursor["exhausted"] = True
        write_cursor(state, cursor)
        session.commit()
        print(
            f"reset {args.source}: page={cursor.get('page')} exhausted={cursor.get('exhausted')} "
            f"cleared={','.join(cleared) or 'nothing'}"
        )
        if not args.page and not args.exhausted and not cleared:
            print("  note: cursor was already clean; use --page N to move it explicitly")
        return 0
    finally:
        session.close()


def cmd_backlog(args) -> int:
    from app.services.policy_collection.ops import backlog_report

    catalog = _catalog()
    session = _session()
    try:
        payload = backlog_report(session, catalog)
    finally:
        session.close()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    print(f"generated_at: {payload['generated_at']}  pause={payload.get('pause')}")
    print(f"  enabled sources        : {payload['enabled_sources']}")
    print(f"  incremental due        : {payload['incremental_due']}")
    print(f"  backfill pending       : {payload['backfill_pending']}")
    print(f"  backfill done          : {payload['backfill_done']}")
    print(f"  backfill unsupported   : {payload['backfill_unsupported']}")
    print(f"  paused sources         : {payload['paused_sources']}")
    print(f"  sources with failures  : {payload['sources_with_failures']}")
    print(f"  runs in flight         : {payload['runs_in_flight']}")
    due = payload.get("incremental_due_sources") or []
    if due:
        print(f"  first due: {', '.join(due[:10])}")
    return 0


def cmd_heartbeat(args) -> int:
    from app.services.policy_collection.ops import heartbeat

    session = _session()
    try:
        payload = heartbeat(session, stale_after_minutes=args.stale_after)
    finally:
        session.close()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    print(
        f"heartbeat: stale={payload['stale']} stale_after={payload['stale_after_minutes']}m "
        f"pause={payload.get('pause')}"
    )
    print(f"  last run started : {payload['last_run_started_at']}")
    print(f"  last run finished: {payload['last_run_finished_at']}")
    print(f"  evidence rows    : {payload['evidence_rows']}")
    if payload["stale"]:
        print("  WARNING: no collection run within the window — check the scheduler.")
    return 0


def cmd_cost(args) -> int:
    from app.services.policy_collection.cost import cost_report

    session = _session()
    try:
        payload = cost_report(session)
    finally:
        session.close()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    budget = payload["budget"]
    usage = payload["consumption"]
    emb = payload["embedding"]
    print(f"generated_at: {payload['generated_at']}")
    print(f"budget: daily_limit={budget['daily_calls_limit']} enabled={budget['enabled']}")
    print(f"consumption: calls_today={usage['calls_today']} metered={usage['metered']}")
    print(f"  note: {usage['note']}")
    print(f"  evidence rows (24h): {usage['evidence_rows_24h']}")
    print(f"embedding: model={emb['model']} dim={emb['dimension']} enabled={emb['vectorisation_enabled']}")
    backlog = emb["backlog"]
    if backlog.get("available"):
        print(
            f"  pending chunks={backlog['pending_chunks']} policies={backlog['pending_policies']} "
            f"embedded={backlog['embedded_chunks']} est_tokens={backlog['estimated_tokens']}"
        )
    else:
        print(f"  backlog unavailable: {backlog.get('error')}")
    print(f"policy: {payload['policy']}")
    return 0


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
    from app.services.policy_collection.ops import write_pause_flag
    from app.services.policy_collection.service import pause_source

    if getattr(args, "global_pause", False) or args.source in ("--global", "all", "*"):
        # Global pause writes a flag file on the persistent volume: it takes effect
        # on the next cycle without restarting the collector, and nothing is
        # deleted — every collected document stays readable while paused.
        path = write_pause_flag(args.reason or "paused by operator")
        print(f"global pause flag written: {path}")
        print("new downloads stop within one cycle; existing policies stay searchable.")
        return 0

    if not args.source:
        print("usage: cli.py pause <source_id> | pause --global [--reason TEXT]")
        return 2

    session = _session()
    try:
        state = pause_source(session, args.source, reason=args.reason or "manual")
        print(f"paused {state.source_id}: {state.paused_reason}")
        print("already-collected policies stay readable; only scheduling stops.")
        return 0
    finally:
        session.close()


def cmd_resume(args) -> int:
    from app.services.policy_collection.ops import clear_pause_flag
    from app.services.policy_collection.service import resume_source

    if getattr(args, "global_pause", False) or args.source in ("--global", "all", "*"):
        removed = clear_pause_flag()
        print("global pause flag removed" if removed else "no global pause flag was set")
        return 0

    if not args.source:
        print("usage: cli.py resume <source_id> | resume --global")
        return 2

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



def cmd_scheduler_once(args) -> int:
    from app.services.policy_collection import scheduler

    catalog = _catalog()
    session = _session()
    try:
        config = scheduler.SchedulerConfig.from_settings(
            max_sources_per_cycle=getattr(args, "max_sources", None),
            cycle_seconds=getattr(args, "seconds", None),
            recheck_interval_hours=getattr(args, "recheck_hours", None),
        )
        result = scheduler.run_cycle(
            session, catalog, config=config, include_recheck=not getattr(args, "no_recheck", False)
        )
        if args.json:
            print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(
                f"cycle {result.stop_reason}: ran={len(result.ran)} skipped={len(result.skipped)} "
                f"due {result.due_before}->{result.due_after} rechecked={len(result.rechecked)}"
            )
            for row in result.ran:
                print(f"  [{row['status']}] {row['source_id']} new={row.get('new')} updated={row.get('updated')}")
            for row in result.skipped:
                print(f"  [skip] {row['source_id']}: {row['reason']}")
        return 0
    finally:
        session.close()


def cmd_scheduler_serve(args) -> int:
    from app.services.policy_collection import scheduler

    catalog = _catalog()
    config = scheduler.SchedulerConfig.from_settings(
        interval_seconds=getattr(args, "interval", None),
        cycle_seconds=getattr(args, "seconds", None),
        max_sources_per_cycle=getattr(args, "max_sources", None),
    )
    print(
        f"scheduler starting: interval={config.interval_seconds}s cycle_budget={config.cycle_seconds}s "
        f"max_sources={config.max_sources_per_cycle} state={config.state_path}",
        flush=True,
    )
    history = scheduler.serve(
        _session,
        lambda: catalog,
        config=config,
        max_cycles=getattr(args, "max_cycles", None),
    )
    if args.json:
        print(json.dumps(history, ensure_ascii=False, indent=2))
    else:
        print(f"scheduler stopped after {len(history)} cycle(s)")
    return 0


def cmd_alerts(args) -> int:
    from app.services.policy_collection import scheduler

    catalog = _catalog()
    session = _session()
    try:
        rows = scheduler.alerts(
            session,
            catalog,
            failure_threshold=getattr(args, "failure_threshold", None),
            stale_hours=getattr(args, "stale_hours", None),
        )
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            if not rows:
                print("no alerts")
            for row in rows:
                print(f"[{row['kind']}] {row.get('source_id') or row.get('scope') or '-'} :: {row.get('action')}")
        return 0 if not [r for r in rows if r["kind"] != "paused"] else 2
    finally:
        session.close()


def cmd_scheduler_status(args) -> int:
    from app.services.policy_collection import scheduler

    config = scheduler.SchedulerConfig.from_settings()
    state = scheduler.scheduler_state(config)
    payload = {
        "state_path": str(config.state_path),
        "last_cycle_finished_at": state.get("last_cycle_finished_at"),
        "last_stop_reason": state.get("last_stop_reason"),
        "due_after": state.get("due_after"),
        "rechecked_sources": len(state.get("rechecked_at") or {}),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="policy collection operations")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("backfill-plan", help="show the next backfill window per source")
    p.add_argument("--sources", help="comma separated source ids (default: prioritised)")
    p.add_argument("--max-sources", type=int)
    p.add_argument("--pages", type=int)
    p.add_argument("--docs", type=int)
    p.add_argument("--seconds", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_backfill_plan)

    for name, func in (("backfill-run", cmd_backfill_run),):
        p = sub.add_parser(name, help="run one bounded historical backfill batch")
        p.add_argument("--sources", help="comma separated source ids")
        p.add_argument("--max-sources", type=int)
        p.add_argument("--pages", type=int, help="list pages per source in this batch")
        p.add_argument("--docs", type=int, help="documents per source in this batch")
        p.add_argument("--seconds", type=int, help="wall-clock budget for the batch")
        p.add_argument("--dry-run", action="store_true", help="no database writes")
        p.add_argument(
            "--enable-collection",
            action="store_true",
            help="explicitly allow this batch to download (collection is off by default)",
        )
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=func)

    p = sub.add_parser("backfill-reset", help="clear a parked/stuck backfill cursor")
    p.add_argument("source", help="source_id whose cursor should be reset")
    p.add_argument("--page", type=int, help="jump the cursor to this list page")
    p.add_argument("--exhausted", action="store_true", help="mark the archive as fully read")
    p.set_defaults(func=cmd_backfill_reset)

    p = sub.add_parser("backfill-status", help="cursor and progress per source")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_backfill_status)

    p = sub.add_parser("cost", help="model budget, consumption and embedding backlog")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_cost)

    p = sub.add_parser("backlog", help="per-queue backlog counts")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_backlog)

    p = sub.add_parser("heartbeat", help="detect stale sources and scheduler health")
    p.add_argument("--stale-after", type=int, default=180)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_heartbeat)

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

    p = sub.add_parser("pause", help="stop scheduling a source, or --global for everything")
    p.add_argument("source", nargs="?", help="source_id, or --global")
    p.add_argument("--global", dest="global_pause", action="store_true", help="pause every source")
    p.add_argument("--reason")
    p.set_defaults(func=cmd_pause)

    p = sub.add_parser("resume", help="resume a paused source, or --global")
    p.add_argument("source", nargs="?", help="source_id, or --global")
    p.add_argument("--global", dest="global_pause", action="store_true", help="lift the global pause")
    p.set_defaults(func=cmd_resume)


    p = sub.add_parser("scheduler-once", help="run exactly one bounded incremental cycle")
    p.add_argument("--max-sources", type=int)
    p.add_argument("--seconds", type=int)
    p.add_argument("--recheck-hours", type=float)
    p.add_argument("--no-recheck", action="store_true", help="skip the slow archive re-check queue")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_scheduler_once)

    p = sub.add_parser("scheduler-serve", help="long-running supervised incremental loop")
    p.add_argument("--interval", type=float, help="seconds between cycles")
    p.add_argument("--seconds", type=int, help="wall-clock budget per cycle")
    p.add_argument("--max-sources", type=int)
    p.add_argument("--max-cycles", type=int, help="stop after N cycles (for smoke tests)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_scheduler_serve)

    p = sub.add_parser("scheduler-status", help="last cycle, stop reason and pending backlog")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_scheduler_status)

    p = sub.add_parser("alerts", help="persistent failures, stale sources and unverified gaps")
    p.add_argument("--failure-threshold", type=int)
    p.add_argument("--stale-hours", type=float)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_alerts)

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
