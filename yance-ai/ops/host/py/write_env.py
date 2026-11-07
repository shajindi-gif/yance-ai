#!/usr/bin/env python3
"""Derive the collector's environment file from the *existing* production env.

Why a Python helper instead of `sed`:
the database password may contain characters that make shell substitution either
wrong (`@`, `$`, `#`) or an injection risk.  Parsing and re-quoting is done with
`urllib.parse`, and the resulting URL is written straight to a 0600 file — it is
never printed, never passed through argv, and never appears in `ps`.

Output is a whitelist.  The collector gets a connection string and its own knobs,
nothing else: no JWT secret, no OSS key, no SMS credential, no API-key pepper.

Usage:
    write_env.py --prod-env /opt/yance/yance-ai/.env.prod \
                 --out /etc/yance/collector.env \
                 --pg-host 127.0.0.1 --pg-port 5434 \
                 --raw-dir /var/lib/yance/policy_raw \
                 --catalog-dir /opt/yance/collector-20261106-r3/config/policy_sources

Exit codes: 0 ok, 2 unreadable/missing inputs, 3 cannot build a usable URL.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import urllib.parse
from pathlib import Path


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def build_database_url(env: dict[str, str], host: str, port: int) -> str:
    """Take the production URL, keep user/password/db, retarget to the loopback port.

    The production compose file binds Postgres to 127.0.0.1:<port>; the collector
    therefore connects over loopback and never needs the port published.
    """
    raw = env.get("DATABASE_URL", "").strip()
    if not raw:
        user = env.get("POSTGRES_USER", "")
        password = env.get("POSTGRES_PASSWORD", "")
        database = env.get("POSTGRES_DB", "")
        if not (user and database):
            raise SystemExit_url("DATABASE_URL absent and POSTGRES_* incomplete")
        raw = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"

    split = urllib.parse.urlsplit(raw)
    user = urllib.parse.unquote(split.username or env.get("POSTGRES_USER", ""))
    password = urllib.parse.unquote(split.password or "")
    if not password:
        password = env.get("POSTGRES_PASSWORD", "")
    database = (split.path or "").lstrip("/") or env.get("POSTGRES_DB", "")
    if not user or not database:
        raise SystemExit_url("cannot determine database user or database name")

    scheme = split.scheme or "postgresql+psycopg"
    query = f"?{split.query}" if split.query else ""
    return (
        f"{scheme}://{urllib.parse.quote(user, safe='')}:"
        f"{urllib.parse.quote(password, safe='')}@{host}:{port}/{database}{query}"
    )


class SystemExit_url(SystemExit):
    def __init__(self, message: str) -> None:
        super().__init__(f"write_env: {message}")
        self.code = 3


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prod-env", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--pg-host", default="127.0.0.1")
    parser.add_argument("--pg-port", type=int, default=5434)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--catalog-dir", required=True)
    parser.add_argument("--min-free-disk-mb", type=int, default=3000)
    args = parser.parse_args(argv)

    prod_env = Path(args.prod_env)
    if not prod_env.is_file():
        print(f"write_env: production env not readable: {prod_env}", file=sys.stderr)
        return 2
    env = read_env_file(prod_env)
    database_url = build_database_url(env, args.pg_host, args.pg_port)

    raw_dir = args.raw_dir.rstrip("/")
    lines = [
        "# Managed by ops/host/install.sh — do not edit by hand.",
        "# Regenerate with: yance-collector env (or rerun install.sh).",
        "# The collector runs on the bare host; it never talks to a Docker network.",
        "",
        "# APP_ENV stays staging on purpose: the collector needs no production",
        "# secrets (JWT / OSS / SMS / API-key pepper) and must not demand them.",
        "APP_ENV=staging",
        "LOG_LEVEL=INFO",
        f"DATABASE_URL={database_url}",
        "DB_POOL_SIZE=5",
        "DB_MAX_OVERFLOW=5",
        "DB_POOL_TIMEOUT=30",
        "",
        "# Collection",
        "POLICY_COLLECTION_ENABLED=true",
        f"POLICY_COLLECTION_RAW_DIR={raw_dir}",
        f"POLICY_COLLECTION_ATTACHMENT_DIR={raw_dir}/attachments",
        f"POLICY_COLLECTION_PAUSE_FLAG_PATH={raw_dir}/PAUSED",
        f"POLICY_COLLECTION_CATALOG_DIR={args.catalog_dir.rstrip('/')}",
        "",
        "# Politeness / rate limiting (per host, not per process)",
        "POLICY_COLLECTION_MIN_HOST_INTERVAL_SECONDS=2.5",
        "POLICY_COLLECTION_REQUEST_TIMEOUT_SECONDS=20",
        "POLICY_COLLECTION_MAX_RETRIES=2",
        "POLICY_COLLECTION_RESPECT_ROBOTS=true",
        'POLICY_COLLECTION_USER_AGENT="YancePolicyCollector/3.0 (+https://yance.ai)"',
        "",
        "# Bounded cycles (2-core host shared with the API and Postgres)",
        "POLICY_COLLECTION_SCHEDULER_CYCLE_SECONDS=600",
        "POLICY_COLLECTION_SCHEDULER_INTERVAL_SECONDS=300",
        "POLICY_COLLECTION_SCHEDULER_MAX_SOURCES_PER_CYCLE=12",
        "POLICY_COLLECTION_MAX_PAGES_PER_SOURCE=3",
        "POLICY_COLLECTION_MAX_ITEMS_PER_SOURCE=20",
        "POLICY_COLLECTION_MAX_DETAIL_BYTES=5000000",
        "",
        "# History backfill: advances a per-source cursor, it does not re-read page 1",
        "POLICY_COLLECTION_BACKFILL_PAGES_PER_BATCH=3",
        "POLICY_COLLECTION_BACKFILL_DOCS_PER_BATCH=15",
        "POLICY_COLLECTION_BACKFILL_WINDOW_SECONDS=600",
        "POLICY_COLLECTION_GAP_STREAK_LIMIT=3",
        "POLICY_COLLECTION_RECHECK_INTERVAL_HOURS=168",
        "",
        "# Disk floor: the guard stops downloads before the volume fills",
        f"POLICY_COLLECTION_MIN_FREE_DISK_MB={args.min_free_disk_mb}",
        "",
        "# No model spend from the collector",
        "POLICY_COLLECTION_LLM_ENABLED=false",
        "POLICY_COLLECTION_DAILY_MODEL_BUDGET_CALLS=0",
        "POLICY_COLLECTION_ATTACHMENT_PARSE_ENABLED=true",
        "",
    ]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(out.parent), prefix=".collector.env.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        os.chmod(tmp, 0o600)
        os.replace(tmp, out)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

    split = urllib.parse.urlsplit(database_url)
    # Fingerprint only: host/port/db/user, and whether a password is present.
    print(
        "write_env: wrote %s (%s:%s%s user=%s password=%s)"
        % (
            out,
            split.hostname,
            split.port,
            split.path,
            split.username,
            "set" if split.password else "UNSET",
        )
    )
    if not split.password:
        print("write_env: WARNING password not set in DATABASE_URL", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SystemExit as exc:
        if isinstance(exc, SystemExit_url):
            print(exc, file=sys.stderr)
        raise
