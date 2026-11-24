#!/usr/bin/env bash
set -Eeuo pipefail
r=/opt/yance/releases/commercial-20261108-01
b=/opt/yance/backups/commercial-20261108-01
base=/opt/yance/releases/sms-20261029-01/yance-ai
rm -f /etc/systemd/system/yance-website.service.d/zzzz-commercial-20261108.conf
ln -sfn "$(cat "$b/website-path.txt")" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f "$b/rollback-api.json" up -d --no-deps --no-build api agent-worker
echo OLD_WEB_API_WORKER_RESTORED_DB_UNCHANGED
