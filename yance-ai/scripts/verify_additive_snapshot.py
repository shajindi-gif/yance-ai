"""Compare pre-migration columns and rows without printing row data.

SOURCE_DATABASE_URL is restricted by the shared snapshot verifier to disposable
local *_test databases. The schema version table is expected to change.
"""

import argparse
import hashlib
import json
from pathlib import Path

from psycopg import sql
from verify_database_snapshot import connect_url


def rows(connection, name, columns):
    query = sql.SQL(
        'SELECT row_to_json(t)::text FROM (SELECT {} FROM {}) t ORDER BY row_to_json(t)::text COLLATE "C"'
    ).format(sql.SQL(",").join(map(sql.Identifier, columns)), sql.Identifier(name))
    digest = hashlib.sha256()
    count = 0
    for (row,) in connection.execute(query):
        digest.update(row.encode())
        digest.update(b"\n")
        count += 1
    return {"rows": count, "sha256": digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["record", "verify"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    with connect_url("SOURCE_DATABASE_URL") as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        if args.phase == "record":
            names = connection.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version' ORDER BY tablename"
            ).fetchall()
            tables = {}
            for (name,) in names:
                columns = [
                    r[0]
                    for r in connection.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
                        (name,),
                    )
                ]
                tables[name] = {"columns": columns, **rows(connection, name, columns)}
            args.path.write_text(json.dumps(tables))
            args.path.chmod(0o600)
            print(json.dumps({"recorded": True, "tables": len(tables)}))
        else:
            before = json.loads(args.path.read_text())
            mismatches = [
                name
                for name, value in before.items()
                if rows(connection, name, value["columns"])
                != {k: value[k] for k in ["rows", "sha256"]}
            ]
            print(
                json.dumps(
                    {
                        "verified": not mismatches,
                        "tables": len(before),
                        "mismatched_tables": mismatches,
                    }
                )
            )
            if mismatches:
                raise SystemExit(1)


if __name__ == "__main__":
    main()
