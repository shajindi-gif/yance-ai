#!/usr/bin/env bash
set -Eeuo pipefail
restore=/opt/yance/releases/website-restore-full-20261028-01
test -f "$restore/.next/BUILD_ID"
conf=/etc/systemd/system/yance-website.service.d/99-full-20261028-01.conf
cat > "$conf.tmp" <<CONFIG
[Service]
WorkingDirectory=$restore
ExecStart=
ExecStart=/usr/bin/node $restore/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Environment=NODE_ENV=production
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
CONFIG
chmod 644 "$conf.tmp"; mv "$conf.tmp" "$conf"
ln -sfn "$restore" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
# Keep database and task history. Backend fallback is maintenance, never downgrade.
echo PREVIOUS_WEBSITE_RESTORED_API_MODE_MUST_BE_CHECKED
