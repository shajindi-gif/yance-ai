"""Compare every public table without printing rows or credentials.

Usage: SOURCE_DATABASE_URL=... RESTORE_DATABASE_URL=... python scripts/verify_database_snapshot.py
Only disposable test databases are accepted. Production restore verification
needs an operator-reviewed equivalent with read-only credentials.
"""
import hashlib
import json
import os

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


def connect_url(key):
    value = os.environ[key]
    url = make_url(value)
    if url.host not in {"127.0.0.1", "localhost"} or not url.database or not url.database.endswith("_test") or "prod" in url.database.lower():
        raise SystemExit("Only local disposable *_test databases are allowed")
    return psycopg.connect(url.set(drivername="postgresql").render_as_string(hide_password=False))


def snapshot(connection):
    tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    result = {}
    for (name,) in tables:
        # Canonical row JSON sorted independently of physical row order. Streams
        # hashes only; no customer fields are written to verification evidence.
        rows = connection.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text COLLATE \"C\"").format(sql.Identifier(name)))
        digest = hashlib.sha256()
        count = 0
        for (row,) in rows:
            digest.update(row.encode())
            digest.update(b"\n")
            count += 1
        result[name] = {"rows":count, "sha256":digest.hexdigest()}
    return result


def main():
    with connect_url("SOURCE_DATABASE_URL") as source, connect_url("RESTORE_DATABASE_URL") as restored:
        for connection in (source, restored):
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        before, after = snapshot(source), snapshot(restored)
    mismatches = [name for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)]
    print(json.dumps({"verified":not mismatches, "table_count":len(before), "row_count":sum(x["rows"] for x in before.values()), "mismatched_tables":mismatches, "tables":before}, sort_keys=True))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
