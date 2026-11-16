#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/payment-metrics-20261115-02
base=/opt/yance/releases/sms-20261029-01/yance-ai
test -s "$r/ci-approved.txt"
test "$(docker image inspect -f '{{.Id}}' yance-backend:payment-metrics-20261115-02)" = "$(cat "$r/approved-image-id.txt")"
python3 - "$r" <<'PY'
import json,subprocess,sys
from pathlib import Path
r=Path(sys.argv[1]);saved=json.loads((r/'rollback.override.json').read_text())['services']
for service,expected in saved.items():
 current=json.loads(subprocess.check_output(['docker','inspect','yance-prod-'+service+'-1']))[0]
 assert current['Image']==expected['image'], 'Production changed since metrics preparation'
PY
dc=(docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f /opt/yance/releases/commercial-20261108-01/api.override.json -f /opt/yance/releases/commercial-20261108-01/quality.override.json -f /opt/yance/releases/payment-20261113-01/release.override.json -f /opt/yance/releases/payment-20261113-01/workers.override.json)
rollback() {
 "${dc[@]}" -f "$r/rollback.override.json" up -d --no-deps --no-build api agent-worker payment-expiry payment-reconcile
 python3 - "$r" <<'PY'
from pathlib import Path
import sys
r=Path(sys.argv[1]);web=Path((r/'website-path.txt').read_text())
for p in [web/'public/release.json',web/'.next/standalone/public/release.json']:p.write_bytes((r/'website-release-before.json').read_bytes());p.chmod(0o644)
PY
}
trap rollback ERR
"${dc[@]}" -f "$r/release.override.json" stop --timeout 120 agent-worker payment-expiry payment-reconcile
"${dc[@]}" -f "$r/release.override.json" up -d --no-deps --no-build api agent-worker payment-expiry payment-reconcile
python3 - "$r" <<'PY'
from pathlib import Path
import json,sys,time,urllib.request,subprocess
r=Path(sys.argv[1]);revision=(r/'SOURCE_REVISION').read_text().strip()
for _ in range(90):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/system/version',timeout=5) as f:version=json.load(f)
  assert version['source_revision']==revision and version['database_revisions']==['20261113_0042']
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Metrics API version check failed')
web=Path((r/'website-path.txt').read_text())
release=json.loads((r/'website-release-before.json').read_text());release.update(api_patch_source=revision,api_release='payment-metrics-20261115-02')
for p in [web/'public/release.json',web/'.next/standalone/public/release.json']:p.write_text(json.dumps(release));p.chmod(0o644)
PY
trap - ERR
echo METRICS_APPLICATION_UPDATE_ACTIVE_NO_DATABASE_MIGRATION
