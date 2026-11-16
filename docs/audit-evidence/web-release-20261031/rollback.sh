#!/usr/bin/env bash
set -Eeuo pipefail
old=/opt/yance/releases/sms-20261029-01
rm -f /etc/systemd/system/yance-website.service.d/zz-web-20261031.conf
ln -sfn "$old/website" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
docker compose -p yance-prod --env-file "$old/yance-ai/.env.prod" -f "$old/yance-ai/docker-compose.prod.yml" -f "$old/yance-ai/release.override.yml" up -d --no-deps --no-build api
printf 'OLD_WEB_AND_API_RESTORED_DB_RETAINED\n'
