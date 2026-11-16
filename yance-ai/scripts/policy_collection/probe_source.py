#!/usr/bin/env python
"""Diagnose why a source's list page yields no entries.

Fetches the entry page through the real fetcher (robots, domain whitelist, rate
limits all applied) and reports what the generic list parser can see:

* byte size, HTTP status, final URL after redirects
* whether the HTML looks client-rendered (no inline list markup, script-driven)
* candidate links the generic heuristics found, and why they were rejected
* any JSON API endpoint or ``__NEXT_DATA__`` style payload embedded in the page

Read-only. Used to decide between "fix selector", "needs site adapter", or
"entry URL is wrong", rather than guessing.

Usage::

    ./.venv/bin/python scripts/policy_collection/probe_source.py nat_miit_policy
    ./.venv/bin/python scripts/policy_collection/probe_source.py prov_zhejiang_kjt_zcfg --dump
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.policy_collection.catalog import load_catalog  # noqa: E402
from app.services.policy_collection.extract import (  # noqa: E402
    extract_list_entries,
    detect_client_redirect,
)
from app.services.policy_collection.fetch import SafeFetcher  # noqa: E402
from app.services.policy_collection.runner import CollectionLimits  # noqa: E402
from app.services.policy_collection.urlguard import TargetPolicy  # noqa: E402

ANCHOR_RE = re.compile(r"<a\b[^>]*href\s*=\s*[\"'](?P<href>[^\"']+)[\"'][^>]*>(?P<text>.*?)</a>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")


def probe(source, dump: bool, follow: bool = False) -> None:
    limits = CollectionLimits.from_settings(settings)
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

    print(f"source       : {source.source_id}")
    print(f"entry_url    : {source.entry_url}")
    page = fetcher.get(source.entry_url, purpose="list")
    print(f"status       : {page.status_code}  error={page.error_kind or '-'}  robots={page.robots_denied}")
    print(f"final_url    : {page.final_url}")
    print(f"bytes        : {len(page.content)}  truncated={page.truncated}  attempts={page.attempts}")
    if not page.ok:
        print("=> list page not retrievable; cannot parse")
        return

    html = page.text
    redirect = detect_client_redirect(html, page.final_url)
    if redirect:
        print(f"client_redirect: {redirect}")
        if follow:
            # The entry URL is a redirect shell; analyse what it actually points at,
            # because that page (not the shell) decides whether a source is workable.
            hopped = fetcher.get(redirect, purpose="list")
            print(
                f"followed     : status={hopped.status_code} bytes={len(hopped.content)} "
                f"ok={hopped.ok} url={hopped.final_url}"
            )
            if hopped.error_kind:
                print(f"follow error : {hopped.error_kind}")
            if hopped.ok:
                page, html = hopped, hopped.text
                second = detect_client_redirect(html, page.final_url)
                if second:
                    print(f"client_redirect(2): {second}")

    entries = extract_list_entries(html, page.final_url)
    print(f"generic_list : {len(entries)} entries")
    for item in entries[:8]:
        print(f"    + {item.date_hint or '-':<10} {item.title[:40]:<42} {item.url[:70]}")

    anchors = list(ANCHOR_RE.finditer(html))
    rel = []
    host = urlparse(page.final_url).netloc
    for match in anchors:
        href = match.group("href").strip()
        if href.startswith(("javascript:", "#", "mailto:")):
            continue
        absolute = urljoin(page.final_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc != host:
            continue
        text = TAG_RE.sub("", match.group("text")).strip()
        if not text or len(text) < 6:
            continue
        rel.append((text, absolute))

    print(f"\nanchors same-host with text>=6 : {len(rel)}")
    seen = set()
    shown = 0
    for text, url in rel:
        if url in seen:
            continue
        seen.add(url)
        if shown >= 15:
            break
        print(f"    {text[:44]:<46} {url[:80]}")
        shown += 1

    hints = []
    if "__NEXT_DATA__" in html:
        hints.append("__NEXT_DATA__")
    if "window.__NUXT__" in html:
        hints.append("__NUXT__")
    if re.search(r"<div[^>]+id=[\"']app[\"']", html, re.I):
        hints.append("#app (vue/react mount)")
    if re.search(r"axios\.|fetch\(|\$\.ajax\(|\$\.get\(", html):
        hints.append("inline ajax call")
    if re.search(r"\.json[\"']", html):
        hints.append("json endpoint string")
    if len(re.findall(r"<script", html, re.I)) > 12 and len(entries) == 0:
        hints.append("script-heavy page")
    print(f"\nclient-render hints: {', '.join(hints) if hints else 'none'}")
    print(f"<li> count: {len(re.findall(r'<li\\b', html, re.I))}   <ul> count: {len(re.findall(r'<ul\\b', html, re.I))}")

    if dump:
        out = Path("crawler_output/probe") / f"{source.source_id}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(page.content)
        print(f"dumped: {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="diagnose a source whose list page yields no entries")
    parser.add_argument("source_id", nargs="+")
    parser.add_argument("--dump", action="store_true", help="save HTML to crawler_output/probe/")
    parser.add_argument(
        "--follow",
        action="store_true",
        help="follow a client-side redirect shell and analyse the page it points to",
    )
    parser.add_argument("--catalog", default=str(settings.policy_collection_catalog_dir))
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    index = {s.source_id: s for s in catalog.sources}
    for sid in args.source_id:
        source = index.get(sid)
        if not source:
            print(f"unknown source: {sid}")
            continue
        probe(source, args.dump, args.follow)
        print("-" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
