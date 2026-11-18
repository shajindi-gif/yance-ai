#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/workspace-20261117-01
b=/opt/yance/backups/workspace-20261117-01
base=/opt/yance/releases/sms-20261029-01/yance-ai
# Approval marker must identify the exact application source that passed CI.
test -s "$r/ci-approved.txt"
test "$(cat "$r/ci-approved.txt")" = "$(cat "$r/SOURCE_REVISION")"
test "$(docker image inspect -f '{{.Id}}' yance-backend:workspace-20261117-01)" = "$(cat "$r/approved-image.txt")"
python3 - "$b" <<'PY'
import json,subprocess,sys
from pathlib import Path
for service,value in json.loads((Path(sys.argv[1])/'rollback.override.json').read_text())['services'].items():
 c=json.loads(subprocess.check_output(['docker','inspect','yance-prod-'+service+'-1']))[0]
 assert c['Image']==value['image'], 'Production changed since preparation'
PY
dc=(docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f /opt/yance/releases/commercial-20261108-01/api.override.json -f /opt/yance/releases/commercial-20261108-01/quality.override.json -f /opt/yance/releases/payment-20261113-01/release.override.json -f /opt/yance/releases/payment-20261113-01/workers.override.json -f /opt/yance/releases/payment-metrics-20261115-02/release.override.json)
rollback() {
 "${dc[@]}" -f "$b/rollback.override.json" up -d --no-deps --no-build api agent-worker payment-expiry payment-reconcile
 rm -f /etc/systemd/system/yance-website.service.d/zzzzzzzzz-workspace-20261117.conf
 ln -sfn "$(cat "$b/website-path.txt")" /opt/yance/website
 systemctl daemon-reload
 systemctl restart yance-website
}
if [ "${1:-}" = rollback ]; then rollback; exit; fi
trap rollback ERR
docker run --rm --network yance-prod_default --env-file "$r/production.env" --entrypoint alembic yance-backend:workspace-20261117-01 upgrade head > "$r/production-migration.log" 2>&1
"${dc[@]}" -f "$r/release.override.json" stop --timeout 120 agent-worker payment-expiry payment-reconcile
"${dc[@]}" -f "$r/release.override.json" up -d --no-deps --no-build api agent-worker payment-expiry payment-reconcile
python3 - "$r" <<'PY'
import json,sys,time,urllib.request
from pathlib import Path
rev=(Path(sys.argv[1])/'SOURCE_REVISION').read_text().strip()
for _ in range(90):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/system/version',timeout=5) as f:v=json.load(f)
  assert v['source_revision']==rev and v['database_revisions']==['20261117_0043']
  break
 except Exception:time.sleep(1)
else:raise RuntimeError('New backend not ready')
PY
old=$(cat "$b/website-path.txt")
python3 "$r/copy_static.py" "$r/website/.next/standalone/.next/static" "$old/.next/standalone/.next/static"
cat > /etc/systemd/system/yance-website.service.d/zzzzzzzzz-workspace-20261117.conf <<CONF
[Service]
WorkingDirectory=$r/website
ExecStart=
ExecStart=/usr/bin/node $r/website/.next/standalone/server.js
Environment=NODE_ENV=production
Environment=HOSTNAME=127.0.0.1
Environment=PORT=3000
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
CONF
ln -sfn "$r/website" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
python3 - "$r" <<'PY'
import json,sys,time,urllib.request
from pathlib import Path
r=Path(sys.argv[1]);rev=(r/'SOURCE_REVISION').read_text().strip()
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=5) as f:w=json.load(f)
  with urllib.request.urlopen('http://127.0.0.1:3000/api/runtime-version',timeout=5) as f:a=json.load(f)
  assert w['website_source']==rev and a['source_revision']==rev and a['database_revisions']==['20261117_0043']
  break
 except Exception:time.sleep(1)
else:raise RuntimeError('New website not ready')
for path in ['/','/pricing','/login','/dashboard','/tasks','/agents','/orders']:
 with urllib.request.urlopen('http://127.0.0.1:3000'+path,timeout=15) as f:assert f.status==200
print('WORKSPACE_PUBLIC_ROUTES_AND_VERSION_PASSED')
PY
systemctl is-active yance-website yance-collector
trap - ERR
echo WORKSPACE_RELEASE_ACTIVE_ASK_REMAINS_CLOSED
