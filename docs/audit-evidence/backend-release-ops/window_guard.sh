#!/usr/bin/env bash
set -eu
release=/opt/yance/releases/backend-7f466d0
if [ ! -f "$release/migration-started" ] && [ "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'SELECT version_num FROM alembic_version;')" = 20261017_0025 ] && [ "$(docker inspect yance-prod-api-1 --format '{{.State.Running}}')" != true ]; then
 docker stop yance-release-maintenance > /dev/null 2>&1 || true
 docker start yance-prod-api-1 yance-prod-agent-worker-1 > /dev/null
 echo PRE_MIGRATION_WINDOW_EXPIRED_BASELINE_RESTORED
fi
