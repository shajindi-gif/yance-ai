"""Print only aggregates/hashes; never customer fields. Retain old columns across additive upgrades."""
import hashlib
import json

from sqlalchemy import text

from app.core.db import SessionLocal

with SessionLocal() as db:
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    for table in ("users", "orders", "payments", "entitlements", "deliverables", "invoices", "invoice_applications"):
        exists = db.scalar(text("SELECT to_regclass(:table)"), {"table": table})
        if not exists:
            continue
        # Added nullable fields are not part of pre-release data identity.
        rows = db.execute(text(f"SELECT (to_jsonb(t) - 'expires_at' - 'paid_at')::text FROM {table} t ORDER BY id")).scalars()
        digest = hashlib.sha256()
        count = 0
        for row in rows:
            digest.update(row.encode()); digest.update(b"\n"); count += 1
        print(json.dumps({"table": table, "count": count, "sha256": digest.hexdigest()}, sort_keys=True))
