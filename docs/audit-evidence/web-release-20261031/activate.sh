#!/usr/bin/env bash
set -Eeuo pipefail
r=/opt/yance/releases/web-20261031-01
b=/opt/yance/backups/web-20261031-01
old=/opt/yance/releases/sms-20261029-01
[ "$(systemctl show yance-website -p WorkingDirectory --value)" = "$old/website" ]
systemctl cat yance-website | cmp -s - "$b/service-before.conf"
grep -q BOTH_CONSENT_VERSIONS_SYNTHETIC_REGISTRATION_PASSED "$r/auth-contract.log"
[ -f "$b/website-before.tar.gz" ]
# Retain content-addressed assets for clients carrying pre-switch HTML in either direction.
cp -an "$r/website/.next/standalone/.next/static/." "$old/website/.next/static/"
trap 'bash "$r/rollback.sh"' ERR
docker compose -p yance-prod --env-file "$old/yance-ai/.env.prod" -f "$old/yance-ai/docker-compose.prod.yml" -f "$old/yance-ai/release.override.yml" -f "$r/compat.override.yml" up -d --no-deps --no-build api
python3 - <<'PY'
import json,time,urllib.request
for _ in range(40):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3) as r:assert json.load(r)['version']=='b408a535+sms-consent-5bd9e19'
  break
 except Exception:time.sleep(1)
else:raise SystemExit('API compatibility image unhealthy')
PY
cat > /etc/systemd/system/yance-website.service.d/zz-web-20261031.conf <<CONF
[Service]
WorkingDirectory=$r/website
ExecStart=
ExecStart=/usr/bin/node $r/website/.next/standalone/server.js
Environment=NODE_ENV=production
Environment=HOSTNAME=127.0.0.1
Environment=PORT=3000
CONF
ln -sfn "$r/website" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
python3 - <<'PY'
import json,time,urllib.request
for _ in range(40):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=3) as r:assert json.load(r)['release']=='web-20261031-01'
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Website unhealthy')
for path in ['/','/login','/pricing','/checkout','/success','/api/v1/auth/config']:
 with urllib.request.urlopen('http://127.0.0.1:3000'+path,timeout=15) as r:assert r.status==200
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=5) as r:
 c=json.load(r);assert c['email_login_enabled'] and c['sms_login_enabled']
print('WEB_RELEASE_ACTIVE_EMAIL_SMS_ENABLED')
PY
[ "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atqc 'select version_num from alembic_version')" = 20261029_0034 ]
systemctl stop yance-web-candidate-1031
trap - ERR
