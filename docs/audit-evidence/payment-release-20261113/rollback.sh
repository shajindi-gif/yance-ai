#!/usr/bin/env bash
set -Eeuo pipefail
r=/opt/yance/releases/payment-20261113-01
b=/opt/yance/backups/payment-20261113-01
base=/opt/yance/releases/sms-20261029-01/yance-ai
dc=(docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f /opt/yance/releases/commercial-20261108-01/api.override.json -f /opt/yance/releases/commercial-20261108-01/quality.override.json)
# No database downgrade or snapshot overwrite. Use only during the controlled
# switch before post-release financial activity; otherwise pause and reconcile.
if [ -f "$r/workers.override.json" ]; then
 "${dc[@]}" -f "$r/release.override.json" -f "$r/workers.override.json" stop --timeout 60 payment-expiry payment-reconcile
fi
"${dc[@]}" -f "$b/rollback.override.json" up -d --no-deps --no-build api agent-worker
if [ -f /etc/systemd/system/yance-website.service.d/zzzzzz-payment-20261113.conf ]; then
 mv /etc/systemd/system/yance-website.service.d/zzzzzz-payment-20261113.conf "$b/failed-payment-dropin.conf"
fi
ln -sfn "$(cat "$b/website-path.txt")" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
python3 - <<'PY'
import time,urllib.request
for url in ['http://127.0.0.1:8000/health/ready','http://127.0.0.1:3000/']:
 for _ in range(60):
  try:
   with urllib.request.urlopen(url,timeout=5) as response:assert response.status==200
   break
  except Exception:time.sleep(1)
 else:raise SystemExit('Restored application readiness failed')
PY
echo OLD_APPLICATIONS_RESTORED_DATABASE_RETAINED
