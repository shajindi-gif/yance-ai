"""Preservation rehearsal: explicit disposable DB only, no supplier calls."""

import json
import os
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
assert os.environ["APP_ENV"] == "test"
assert url.host in {"localhost", "127.0.0.1"} and url.database.endswith("_test")
assert os.environ["YANCE_TEST_DATABASE_ACK"] == url.database
engine = create_engine(url)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "20261027_0033"], check=True)
with engine.begin() as db:
    tenant, user = uuid.uuid4(), uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO tenants (id,name,slug,is_active,account_stage,created_at,updated_at) VALUES (:id,'Synthetic existing tenant',:slug,true,'trial',now(),now())"
        ),
        {"id": tenant, "slug": str(tenant)},
    )
    db.execute(
        text(
            "INSERT INTO users (id,tenant_id,email,full_name,password_hash,role,is_active,is_platform_admin,auth_version,created_at,updated_at) VALUES (:id,:tenant,'existing@example.com','Synthetic existing user','unchanged-test-hash','owner',true,false,7,now(),now())"
        ),
        {"id": user, "tenant": tenant},
    )
    before = db.scalar(text("SELECT to_jsonb(u)::text FROM users u WHERE id=:id"), {"id": user})
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
with engine.connect() as db:
    after = db.scalar(
        text("SELECT (to_jsonb(u)-'phone')::text FROM users u WHERE id=:id"), {"id": user}
    )
    assert json.loads(before) == json.loads(after)
subprocess.run([sys.executable, "-m", "alembic", "check"], check=True)
print(
    json.dumps(
        {
            "existing_user_all_original_fields_preserved": True,
            "revision": "20261029_0034",
            "synthetic_only": True,
        }
    )
)
