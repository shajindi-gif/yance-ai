#!/usr/bin/env python
"""One-off source verification probe.

For each candidate host it performs a single polite request to the site root,
records the real HTTP outcome and lists the navigation links whose text looks
like a policy / notice / application column. Output is JSON on stdout so the
catalogue can be built from measured facts instead of guessed URLs.

Usage:
    python -m scripts.policy_collection.probe_sites --hosts hosts.txt --out temp/probe.json
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

from app.services.policy_collection.extract import _clean, _PageParser

KEYWORDS = (
    "政策",
    "文件",
    "通知",
    "公告",
    "申报",
    "公示",
    "法规",
    "规章",
    "惠企",
    "科技",
)


@dataclass
class ProbeResult:
    host: str
    url: str
    status_code: int | None = None
    final_url: str | None = None
    title: str | None = None
    server: str | None = None
    error: str | None = None
    columns: list[dict] = field(default_factory=list)


def probe(host: str, client: httpx.Client) -> ProbeResult:
    url = host if host.startswith("http") else f"https://{host}/"
    result = ProbeResult(host=host, url=url)
    try:
        response = client.get(url)
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"[:200]
        return result
    result.status_code = response.status_code
    result.final_url = str(response.url)
    result.server = response.headers.get("server")
    if response.status_code >= 400:
        result.error = f"http {response.status_code}"
        return result
    parser = _PageParser()
    try:
        parser.feed(response.text)
        parser.close()
    except Exception as exc:
        result.error = f"parse: {exc}"[:200]
        return result
    result.title = _clean("".join(parser.title_text))[:80]
    seen: set[str] = set()
    for link in parser.links:
        label = link.label
        if len(label) < 2 or len(label) > 40:
            continue
        if not any(keyword in label for keyword in KEYWORDS):
            continue
        absolute = urljoin(result.final_url, link.href)
        if (urlparse(absolute).hostname or "") != (urlparse(result.final_url).hostname or ""):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        result.columns.append({"text": label, "url": absolute})
        if len(result.columns) >= 40:
            break
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hosts", required=True, help="file with one host per line")
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=float, default=1.5)
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()

    hosts = [
        line.strip()
        for line in open(args.hosts, encoding="utf-8")
        if line.strip() and not line.startswith("#")
    ]
    results: list[dict] = []
    with httpx.Client(
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
        headers={
            "User-Agent": "YancePolicyCollector/3.0 (+policy-source-verification)",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    ) as client:
        for host in hosts:
            result = probe(host, client)
            results.append(asdict(result))
            print(
                f"{host}\t{result.status_code}\t{result.error or 'ok'}\t{result.title or ''}",
                flush=True,
            )
            time.sleep(args.interval)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)
    print(f"written {args.out}")


if __name__ == "__main__":
    main()
