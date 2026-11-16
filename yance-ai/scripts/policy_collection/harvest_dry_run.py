#!/usr/bin/env python
"""Read-only harvest dry run: fetch real list pages and a few documents, no DB.

Purpose
-------
``cli.py run`` needs PostgreSQL because it stores versions, chunks and runs.
That blocks the honest question "do the adapters actually work on the real
sites?" on a machine with no database. This script answers exactly that,
without touching any database or model:

* one request for the list page per source (through the same adapter path)
* up to ``--docs`` document pages per source
* parse through the real ``extract_document_page``
* write the raw bytes to a scratch directory so nothing is claimed without evidence

Output is a per-source table with parsed / thin / failed counts plus a JSON
summary. Anything it cannot verify is reported as such, never assumed.

Usage (from ``yance-ai/``)::

    ./.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level national --docs 2
    ./.venv/bin/python scripts/policy_collection/harvest_dry_run.py --source nat_gov_policy,prov_zhejiang_kjt
    ./.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level municipal --limit 10 --docs 1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
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
from app.services.policy_collection.extract import (  # noqa: E402
    extract_document_page,
)
from app.services.policy_collection.fetch import SafeFetcher  # noqa: E402
from app.services.policy_collection.runner import CollectionLimits  # noqa: E402
from app.services.policy_collection.urlguard import TargetPolicy  # noqa: E402

THIN_CHARS = 200


@dataclass
class DocResult:
    url: str
    ok: bool
    parsed: bool = False
    chars: int = 0
    title: str = ""
    doc_number: str | None = None
    published_at: str | None = None
    attachments: int = 0
    error: str | None = None


@dataclass
class SourceResult:
    source_id: str
    level: str
    province: str | None
    city: str | None
    list_ok: bool = False
    entries: int = 0
    adapter: str = ""
    list_error: str | None = None
    docs: list[DocResult] = field(default_factory=list)

    @property
    def parsed_docs(self) -> int:
        return sum(1 for d in self.docs if d.parsed)

    @property
    def thin_docs(self) -> int:
        return sum(1 for d in self.docs if d.ok and not d.parsed)


def _fetcher(source, limits) -> SafeFetcher:
    return SafeFetcher(
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


def run_one(source, *, docs: int, limits, raw_root: Path) -> SourceResult:
    result = SourceResult(
        source_id=source.source_id,
        level=source.level,
        province=source.province,
        city=source.city,
    )
    fetcher = _fetcher(source, limits)
    adapter = resolve_adapter(source)
    try:
        fetched = adapter.fetch(fetcher, source, max_pages=1)
    except ListUnavailable as exc:
        result.list_error = f"{exc}"[:200]
        return result
    except Exception as exc:  # noqa: BLE001 - dry run must never crash the batch
        result.list_error = f"{type(exc).__name__}: {exc}"[:200]
        return result

    result.list_ok = True
    result.entries = len(fetched.entries)
    result.adapter = fetched.adapter_used

    for entry in fetched.entries[:docs]:
        entry_url = entry.url
        doc = DocResult(url=entry_url, ok=False)
        try:
            page = fetcher.get(entry_url)
        except Exception as exc:  # noqa: BLE001
            doc.error = f"fetch {type(exc).__name__}"[:80]
            result.docs.append(doc)
            continue
        if not page.ok:
            doc.error = f"http {page.status_code} {page.error_kind or ''}".strip()[:80]
            result.docs.append(doc)
            continue
        html = page.text
        parsed = extract_document_page(html, entry_url)
        doc.ok = True
        doc.chars = len(parsed.text or "")
        doc.title = (parsed.title or "")[:80]
        doc.doc_number = parsed.doc_number
        doc.published_at = parsed.published_at.isoformat() if parsed.published_at else None
        doc.attachments = len(parsed.attachments or [])
        doc.parsed = doc.chars >= THIN_CHARS

        target_dir = raw_root / source.source_id
        target_dir.mkdir(parents=True, exist_ok=True)
        name = entry_url.rstrip("/").rsplit("/", 1)[-1] or "index"
        name = "".join(ch for ch in name if ch.isalnum() or ch in "-_.")[:80] or "doc"
        (target_dir / f"{name}.html").write_bytes(page.content)

        result.docs.append(doc)
        time.sleep(limits.min_host_interval_seconds)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="read-only harvest dry run (no DB, no model)")
    parser.add_argument("--level", choices=["national", "provincial", "municipal", "all"], default="all")
    parser.add_argument("--source", default="", help="comma separated source_id list")
    parser.add_argument("--limit", type=int, default=0, help="max sources to touch")
    parser.add_argument("--docs", type=int, default=2, help="document pages per source")
    parser.add_argument("--catalog", default=str(settings.policy_collection_catalog_dir))
    parser.add_argument("--out", default="", help="JSON summary path")
    parser.add_argument("--raw-root", default="crawler_output/dry_run", help="where raw bytes land")
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    targets = [s for s in catalog.sources if s.enabled]
    if args.level != "all":
        targets = [s for s in targets if s.level == args.level]
    if args.source:
        wanted = {item.strip() for item in args.source.split(",") if item.strip()}
        targets = [s for s in catalog.sources if s.source_id in wanted]
    if args.limit:
        targets = targets[: args.limit]

    limits = CollectionLimits.from_settings(settings)
    raw_root = Path(args.raw_root)
    raw_root.mkdir(parents=True, exist_ok=True)

    print(f"dry run: {len(targets)} source(s), {args.docs} doc(s) each, no DB, no model\n")
    results: list[SourceResult] = []
    for source in targets:
        res = run_one(source, docs=args.docs, limits=limits, raw_root=raw_root)
        results.append(res)
        if not res.list_ok:
            print(f"LIST-FAIL {res.source_id:<32} {res.list_error}")
            continue
        print(
            f"OK        {res.source_id:<32} entries={res.entries:<3} "
            f"parsed={res.parsed_docs}/{len(res.docs)} adapter={res.adapter}"
        )
        for doc in res.docs:
            mark = "parsed" if doc.parsed else ("thin" if doc.ok else "fail")
            print(
                f"    - {mark:<6} chars={doc.chars:<5} "
                f"date={doc.published_at or '-':<10} docno={(doc.doc_number or '-')[:18]:<18} "
                f"att={doc.attachments} {doc.title[:34]}"
            )

    list_ok = [r for r in results if r.list_ok]
    parsed_total = sum(r.parsed_docs for r in results)
    docs_total = sum(len(r.docs) for r in results)
    with_date = sum(1 for r in results for d in r.docs if d.published_at)
    with_docno = sum(1 for r in results for d in r.docs if d.doc_number)
    with_att = sum(1 for r in results for d in r.docs if d.attachments)

    summary = {
        "sources_attempted": len(results),
        "sources_list_ok": len(list_ok),
        "sources_list_failed": len(results) - len(list_ok),
        "documents_fetched": docs_total,
        "documents_parsed": parsed_total,
        "documents_thin": sum(1 for r in results for d in r.docs if d.ok and not d.parsed),
        "documents_failed": sum(1 for r in results for d in r.docs if not d.ok),
        "with_published_date": with_date,
        "with_doc_number": with_docno,
        "with_attachments": with_att,
        "by_level": {
            lvl: {
                "sources": sum(1 for r in results if r.level == lvl),
                "list_ok": sum(1 for r in results if r.level == lvl and r.list_ok),
                "parsed": sum(r.parsed_docs for r in results if r.level == lvl),
            }
            for lvl in ("national", "provincial", "municipal")
        },
        "sources": [
            {
                "source_id": r.source_id,
                "level": r.level,
                "province": r.province,
                "city": r.city,
                "list_ok": r.list_ok,
                "entries": r.entries,
                "adapter": r.adapter,
                "list_error": r.list_error,
                "docs": [d.__dict__ for d in r.docs],
            }
            for r in results
        ],
    }

    print("\n=== summary ===")
    print(f"sources: {len(list_ok)}/{len(results)} list-ok, {len(results)-len(list_ok)} failed")
    print(
        f"documents: {parsed_total}/{docs_total} parsed, "
        f"{summary['documents_thin']} thin, {summary['documents_failed']} failed"
    )
    print(f"fields: date {with_date}, docno {with_docno}, attachments {with_att}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"written: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
