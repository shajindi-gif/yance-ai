#!/usr/bin/env bash
set -euo pipefail
umask 077
release=/opt/yance/releases/website-web-20261026-01
old=/opt/yance/releases/website-web-20261025-01/website
[ "$(systemctl show yance-website -p WorkingDirectory --value)" = "$old" ]
[ -f /opt/yance/backups/website-web-20261026-01/website-before.sha256 ]
[ -f "$release/website/.next/BUILD_ID" ]
# Freeze the existing service state; do not overwrite an intervening configuration change.
systemctl cat yance-website | cmp -s - /opt/yance/backups/website-web-20261026-01/service-before.conf
trap 'bash "$release/ops/rollback.sh"' ERR
conf=/etc/systemd/system/yance-website.service.d/91-website-web-20261026-01.conf
cat > "$conf.tmp" <<CONFIG
[Service]
WorkingDirectory=$release/website
ExecStart=
ExecStart=/usr/bin/node $release/website/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Environment=NODE_ENV=production
CONFIG
chmod 644 "$conf.tmp"
mv "$conf.tmp" "$conf"
ln -sfn "$release/website" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
python3 - <<'PY'
import time,json,urllib.request
base='http://127.0.0.1:3000'
for attempt in range(30):
 try:
  with urllib.request.urlopen(base+'/release.json',timeout=3) as r:
   if json.load(r)['release']=='web-20261026-01':break
 except Exception:pass
 time.sleep(1)
else:raise SystemExit('New website failed to start')
for path in ['/','/pricing','/feedback','/login','/security','/product/evidence-workspace.png','/api/v1/products','/api/v1/auth/config']:
 with urllib.request.urlopen(base+path,timeout=15) as r:
  assert r.status==200
  print(path,r.status,len(r.read()))
with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=10) as r:
 assert json.load(r)['version']=='e58a7c46d6ed296aa1854455b3f4a4d4940afc35'
print('ACTIVATION_READY_BACKEND_UNCHANGED')
PY
trap - ERR
date -u +%FT%TZ
