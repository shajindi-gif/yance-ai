#!/usr/bin/env bash
set -Eeuo pipefail
old=/opt/yance/releases/full-20261028-01
test -f "$old/website/.next/BUILD_ID"
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'select version_num from alembic_version;')" = 20261027_0033
docker compose -p yance-prod --env-file "$old/yance-ai/.env.prod" -f "$old/yance-ai/docker-compose.prod.yml" -f "$old/yance-ai/release.override.yml" up -d --no-deps --no-build --timeout 60 api agent-worker
rm -f /etc/systemd/system/yance-website.service.d/99-growth-20261029-01.conf
ln -sfn "$old/website" /opt/yance/website
ln -sfn "$old/yance-ai" /opt/yance/yance-ai
systemctl daemon-reload
systemctl restart yance-website
echo APPLICATION_ROLLBACK_STARTED_VERIFY_HEALTH_AND_PAYMENTS_DATABASE_NOT_CHANGED
