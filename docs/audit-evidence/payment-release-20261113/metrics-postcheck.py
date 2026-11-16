"""Read-only acceptance after the metrics-only application update."""
import json
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

r = Path("/opt/yance/releases/payment-metrics-20261115-02")
revision = (r / "SOURCE_REVISION").read_text().strip()
names = ["yance-prod-"+name+"-1" for name in ["api", "agent-worker", "payment-expiry", "payment-reconcile"]]
for _ in range(90):
    containers = json.loads(subprocess.check_output(["docker", "inspect", *names]))
    if all(c["State"].get("Health", {}).get("Status") == "healthy" for c in containers):
        break
    time.sleep(1)
else:
    raise SystemExit("Metrics release readiness failed")
assert all(c["Image"] == (r/"approved-image-id.txt").read_text() for c in containers)
with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/system/version", timeout=10) as response:
    version = json.load(response)
assert version["source_revision"] == revision and version["database_revisions"] == ["20261113_0042"]
code = '''
import json
from sqlalchemy import text
from app.core.db import SessionLocal
from app.services.admin.metrics import investor_metrics
with SessionLocal() as db:
 db.execute(text("SET TRANSACTION READ ONLY"))
 m=investor_metrics(db)
 print(json.dumps({'paying_customers':m['totals']['paying_customers'],'recognized_revenue':m['revenue_by_currency'],'unverified_paid_orders':m['totals']['unverified_paid_orders'],'payment_channels':[list(x) for x in db.execute(text('SELECT provider,status,count(*) FROM payments GROUP BY provider,status ORDER BY provider,status'))]}))
'''
metrics = json.loads(subprocess.run(["docker", "exec", "-i", "yance-prod-api-1", "python", "-"], input=code, text=True, capture_output=True, check=True).stdout)
services = subprocess.check_output(["systemctl", "is-active", "yance-website", "yance-collector"], text=True).splitlines()
assert services == ["active", "active"]
result = {"checked_at": datetime.now(UTC).isoformat(), "runtime": version,
          "containers": [{"name": c["Name"], "health": c["State"]["Health"]["Status"]} for c in containers],
          "services": {"website": "active", "policy_collector": "active"},
          "metrics": metrics, "image": json.loads((r/"image-summary.json").read_text()),
          "database_migration_executed": False, "real_transactions_executed": False}
(r/"postcheck.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result))
