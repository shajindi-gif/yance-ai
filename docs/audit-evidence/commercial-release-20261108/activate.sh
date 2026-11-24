#!/usr/bin/env bash
set -Eeuo pipefail
r=/opt/yance/releases/commercial-20261108-01
b=/opt/yance/backups/commercial-20261108-01
base=/opt/yance/releases/sms-20261029-01/yance-ai
grep -q PREPARED_BACKUP_RESTORED_API_ISOLATED_WEB_BUILT /home/ubuntu/yance-commercial-1108-prepare.log
grep -q PG16_SYNTHETIC_REGISTRATION_EVIDENCE_VERSION_READ_PASSED "$r/candidate-check.log"
grep -q CANDIDATE_BROWSER_PASSED "$r/browser-approved.txt"
[ "$(readlink -f /opt/yance/website)" = "$(cat "$b/website-path.txt")" ]
[ "$(docker inspect -f '{{.Image}}' yance-prod-api-1)" = "$(cat "$b/api-image.txt")" ]
trap 'bash "$r/rollback.sh"' ERR
# Both sides retain content-addressed chunks for browsers carrying cached HTML.
cp -an "$r/website/.next/standalone/.next/static/." "$(cat "$b/website-path.txt")/.next/standalone/.next/static/"
docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f "$r/api.override.json" stop --timeout 120 agent-worker
docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f "$r/api.override.json" up -d --no-deps --no-build api agent-worker
python3 - <<'PY'
import json,time,urllib.request
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/system/version',timeout=3) as f:v=json.load(f)
  assert v['source_revision']=='68b3d5b' and v['database_revisions']==['20261106_0038']
  break
 except Exception:time.sleep(1)
else:raise SystemExit('API revision check failed')
PY
cat > /etc/systemd/system/yance-website.service.d/zzzz-commercial-20261108.conf <<CONF
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
python3 - <<'PY'
import json,time,urllib.request
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/api/runtime-version',timeout=5) as f:v=json.load(f)
  assert v['source_revision']=='68b3d5b' and v['database_revisions']==['20261106_0038']
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Web/API runtime version check failed')
for path in ['/','/login','/pricing','/discover','/checkout','/success']:
 with urllib.request.urlopen('http://127.0.0.1:3000'+path,timeout=15) as f:assert f.status==200
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=5) as f:c=json.load(f)
assert c['email_login_enabled'] and c['sms_login_enabled']
print('COMMERCIAL_RELEASE_ACTIVE_EMAIL_SMS_ENABLED_DB0038')
PY
trap - ERR
