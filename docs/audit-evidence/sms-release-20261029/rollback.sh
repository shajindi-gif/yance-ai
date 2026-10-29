#!/usr/bin/env bash
# Before SMS activation (no phone-only accounts), restore both old apps.
# After phone-only signup, retain data and fail closed for forward recovery.
set -Eeuo pipefail
r=/opt/yance/releases/sms-20261029-01
old=/opt/yance/releases/growth-20261029-01
web=/opt/yance/releases/website-images-20261029-01/website
docker stop -t 60 yance-prod-api-1 yance-prod-agent-worker-1 >/dev/null 2>&1 || true
phone_only=$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atqc 'select count(*) from users where email is null;')
rm -f /etc/systemd/system/yance-website.service.d/99-sms-20261029-01.conf
ln -sfn "$web" /opt/yance/website
systemctl daemon-reload; systemctl restart yance-website
if [[ "$phone_only" = 0 ]];then
 docker stop yance-sms-maintenance >/dev/null 2>&1 || true
 docker compose -p yance-prod --env-file "$old/yance-ai/.env.prod" -f "$old/yance-ai/docker-compose.prod.yml" -f "$old/yance-ai/release.override.yml" up -d --no-deps --no-build api agent-worker
 ln -sfn "$old/yance-ai" /opt/yance/yance-ai
 echo OLD_APPS_RESTORED_SCHEMA_RETAINED
else
 docker start yance-sms-maintenance >/dev/null 2>&1 || docker run -d --name yance-sms-maintenance --restart unless-stopped --memory 96m -p 127.0.0.1:8000:8000 -v "$r/ops/maintenance.py:/maintenance.py:ro" -v "$r/catalogue.json:/catalogue.json:ro" --entrypoint python yance-backend:sms-20261029-01 /maintenance.py >/dev/null
 echo PHONE_IDENTITIES_RETAINED_API_MAINTENANCE_FORWARD_REPAIR_REQUIRED
fi
