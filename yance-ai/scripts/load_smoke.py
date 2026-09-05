"""Bounded HTTP concurrency smoke test; not a production capacity benchmark."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * ratio) - 1)
    return ordered[index]


def request_once(client: httpx.Client, url: str) -> tuple[int, float, str | None]:
    started = time.perf_counter()
    try:
        response = client.get(url)
        return response.status_code, (time.perf_counter() - started) * 1000, None
    except httpx.HTTPError as exc:
        return 0, (time.perf_counter() - started) * 1000, type(exc).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=5)
    parser.add_argument("--max-p95-ms", type=float, default=750)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("requests and concurrency must be positive")

    started = time.perf_counter()
    results: list[tuple[int, float, str | None]] = []
    with (
        httpx.Client(timeout=args.timeout_seconds, trust_env=False) as client,
        ThreadPoolExecutor(max_workers=min(args.concurrency, args.requests)) as pool,
    ):
        futures = [pool.submit(request_once, client, args.url) for _ in range(args.requests)]
        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.perf_counter() - started
    durations = [duration for _, duration, _ in results]
    successful = sum(1 for status, _, _ in results if 200 <= status < 400)
    errors = Counter(error for _, _, error in results if error)
    report = {
        "scope": "bounded_http_smoke_not_capacity_benchmark",
        "url": args.url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "successful": successful,
        "failed": args.requests - successful,
        "errors": dict(sorted(errors.items())),
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(args.requests / elapsed, 2),
        "latency_ms": {
            "mean": round(statistics.fmean(durations), 2),
            "p50": round(percentile(durations, 0.50), 2),
            "p95": round(percentile(durations, 0.95), 2),
            "p99": round(percentile(durations, 0.99), 2),
        },
        "thresholds": {"success_rate": 1.0, "max_p95_ms": args.max_p95_ms},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if successful == args.requests and report["latency_ms"]["p95"] <= args.max_p95_ms else 1


if __name__ == "__main__":
    raise SystemExit(main())
