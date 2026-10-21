#!/usr/bin/env bash
set -Eeuo pipefail
release=/opt/yance/releases/backend-7f466d0
restore_before_migration() {
 code=$?
 docker stop yance-release-maintenance > /dev/null 2>&1 || true
 docker start yance-prod-api-1 yance-prod-agent-worker-1 > /dev/null
 exit "$code"
}
trap restore_before_migration ERR
# Preserve old image identity and original runtime/config; never remove DB volumes.
docker inspect yance-prod-api-1 --format '{{.Image}}' > "$release/previous-image-id.txt"
docker tag "$(cat "$release/previous-image-id.txt")" yance-backend:before-7f466d0
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'SELECT version_num FROM alembic_version;')" = 20261017_0025
echo STOPPING_OLD_WORKER
docker stop -t 150 yance-prod-agent-worker-1 > /dev/null
echo STOPPING_OLD_API
docker stop -t 150 yance-prod-api-1 > /dev/null
docker run -d --name yance-release-maintenance --restart unless-stopped --memory 96m -p 127.0.0.1:8000:8000 -v "$release/maintenance.py:/maintenance.py:ro" -v "$release/catalogue.json:/catalogue.json:ro" --entrypoint python yance-backend:7f466d0 /maintenance.py > /dev/null
echo PROTECTED_MAINTENANCE_ACTIVE
python3 /tmp/yance-backup-restore-verify.py /opt/yance-backups/release-7f466d0-final
