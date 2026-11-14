#!/bin/bash
set -Eeuo pipefail
r=/opt/yance/releases/frontend-20261109-01
b=/opt/yance/backups/frontend-20261109-01
grep -q CANDIDATE_BUILD_AND_SEVEN_PAGES_PASSED /home/ubuntu/yance-intelligence-prepare.log
test -f "$r/browser-approved"
[ "$(readlink -f /opt/yance/website)" = "$(cat "$b/website-path.txt")" ]
trap 'bash "$r/rollback.sh"' ERR
cp -an "$r/website/.next/standalone/.next/static/." "$(cat "$b/website-path.txt")/.next/standalone/.next/static/"
cat > /etc/systemd/system/yance-website.service.d/zzzzzz-frontend-20261109.conf <<CONF
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
import urllib.request,json,time
for _ in range(40):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=3) as f:assert json.load(f)['website_source']=='680e048'
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Website version check failed')
for path in ['/','/login','/pricing','/discover','/orders','/applications','/security','/intelligence']:
 with urllib.request.urlopen('http://127.0.0.1:3000'+path,timeout=10) as f:assert f.status==200
with urllib.request.urlopen('http://127.0.0.1:3000/api/runtime-version',timeout=10) as f:v=json.load(f)
assert v['source_revision']=='68b3d5b' and v['database_revisions']==['20261109_0039']
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=5) as f:c=json.load(f)
assert c['email_login_enabled'] and c['sms_login_enabled']
print('FRONTEND_FAF50B6_API68_DB0038_EMAIL_SMS_PASSED')
PY
systemctl is-active yance-website yance-collector
trap - ERR
