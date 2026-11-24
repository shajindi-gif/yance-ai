"""Read-only release identity, health, collector continuity and ledger counts."""
import json
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

r = Path("/opt/yance/releases/payment-20261113-01")
revision = (r / "SOURCE_REVISION").read_text().strip()
expected_image = (r / "approved-image-id.txt").read_text().strip()


def get(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


runtime = get("http://127.0.0.1:8000/api/v1/system/version")
assert runtime["source_revision"] == revision
assert runtime["database_revisions"] == ["20261113_0042"]
assert get("http://127.0.0.1:3000/release.json")["website_source"] == revision
names = ["yance-prod-api-1", "yance-prod-agent-worker-1", "yance-prod-payment-expiry-1", "yance-prod-payment-reconcile-1"]
for _ in range(90):
    containers = json.loads(subprocess.check_output(["docker", "inspect", *names]))
    if all(c["State"].get("Health", {}).get("Status") == "healthy" for c in containers):
        break
    time.sleep(1)
else:
    raise SystemExit("Release container readiness failed")
assert all(c["Image"] == expected_image for c in containers)
services = subprocess.check_output(["systemctl", "is-active", "yance-website", "yance-collector"], text=True).splitlines()
assert services == ["active", "active"]
read_script = '''
from sqlalchemy import text
from app.core.db import SessionLocal
with SessionLocal() as db:
 db.execute(text("SET TRANSACTION READ ONLY"))
 for table in ['orders','payments','refunds','reconciliation_runs']:
  print(table,db.execute(text('SELECT status,count(*) FROM '+table+' GROUP BY status ORDER BY status')).all())
 print('payment_channels',db.execute(text('SELECT provider,status,count(*) FROM payments GROUP BY provider,status ORDER BY provider,status')).all())
 print('paid_tenant_class',db.execute(text('SELECT t.is_demo,t.account_stage,count(*) FROM orders o JOIN tenants t ON t.id=o.tenant_id WHERE o.status=:status GROUP BY t.is_demo,t.account_stage'),{'status':'paid'}).all())
'''
counts = subprocess.run(["docker", "exec", "-i", "yance-prod-api-1", "python", "-"], input=read_script, text=True, capture_output=True, check=True).stdout
scan = json.loads((r / "actual-image-scan.json").read_text())
assert not [v for x in scan.get("Results", []) for v in x.get("Vulnerabilities") or []]
result = {"checked_at": datetime.now(UTC).isoformat(), "runtime": runtime,
          "image_identity": json.loads((r / "image-identity.json").read_text()),
          "services": {"website": "active", "policy_collector": "active"},
          "containers": [{"name": c["Name"], "health": c["State"]["Health"]["Status"], "image": c["Image"]} for c in containers],
          "financial_status_counts": counts.splitlines(),
          "actual_image_fixed_high_critical": 0,
          "backup_restored_before_migration": (r / "preswitch-before.log").read_bytes() == (r / "preswitch-after.log").read_bytes(),
          "real_charge_refund_invoice_tests_executed": False}
assert result["backup_restored_before_migration"]
(r / "postcheck.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
