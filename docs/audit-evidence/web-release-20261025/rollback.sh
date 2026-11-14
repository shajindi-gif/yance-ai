#!/usr/bin/env bash
set -euo pipefail
umask 077
restore=/opt/yance/releases/website-rollback-web-20261025-01/website
release=/opt/yance/releases/website-web-20261025-01
conf=/etc/systemd/system/yance-website.service.d/91-website-web-20261025-01.conf
[ -f "$restore/.next/BUILD_ID" ]
[ "$(node -p 'require(process.argv[1]).version' "$restore/node_modules/next/package.json")" = 16.4.3 ]
cat > "$conf.tmp" <<CONFIG
[Service]
WorkingDirectory=$restore
ExecStart=
ExecStart=/usr/bin/node $restore/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Environment=NODE_ENV=production
CONFIG
chmod 644 "$conf.tmp"
mv "$conf.tmp" "$conf"
ln -sfn "$restore" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
python3 - <<'PY'
import time,json,urllib.request
for attempt in range(30):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=3) as r:
   if json.load(r)['release']=='web-20261020-01':print('ROLLBACK_OLD_WEBSITE_READY');break
 except Exception: pass
 time.sleep(1)
else:raise SystemExit('Rollback health check failed')
PY
