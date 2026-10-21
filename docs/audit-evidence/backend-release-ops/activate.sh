#!/usr/bin/env bash
set -Eeuo pipefail
release=/opt/yance/releases/backend-7f466d0
code="$release/yance-ai"
expected=7f466d0b34e0f52a64058d64d6406b7132bca775
compose=(docker compose -p yance-prod --env-file "$code/.env.prod" -f "$code/docker-compose.prod.yml" -f "$code/release.override.yml")
fallback() {
  result=$?
  echo ACTIVATION_FAILED_PROTECTING_DATA
  docker stop -t 30 yance-prod-api-1 yance-prod-agent-worker-1 > /dev/null 2>&1 || true
  if ! docker start yance-release-maintenance > /dev/null 2>&1; then
    docker run -d --name yance-release-maintenance --restart unless-stopped --memory 96m -p 127.0.0.1:8000:8000 -v "$release/maintenance.py:/maintenance.py:ro" -v "$release/catalogue.json:/catalogue.json:ro" --entrypoint python yance-backend:7f466d0 /maintenance.py > /dev/null
  fi
  echo 'Database retained; do not downgrade or restore old authentication. Forward repair required.'
  exit "$result"
}
trap fallback ERR
# The final backup must already have passed recovery and off-box verification.
test -f "$release/offbox-final-verified.json"
python3 -c 'import json; r=json.load(open("/opt/yance-backups/release-7f466d0-final/verification.json")); p=json.load(open("/opt/yance/releases/backend-7f466d0/offbox-final-verified.json")); assert r["verified"] and p["verified"] and p["plain_sha256"]==r["plain_sha256"] and p["cipher_sha256"]==r["cipher_sha256"]'
touch "$release/migration-started"
"${compose[@]}" run --rm --no-deps -T -e PGOPTIONS='-c lock_timeout=5000 -c statement_timeout=30000' migrate alembic upgrade head
python3 /tmp/yance-verify-final-production-migration.py
docker stop yance-release-maintenance > /dev/null
"${compose[@]}" up -d --no-deps --no-build api agent-worker
for attempt in {1..40}; do
  if curl --max-time 3 -fsS http://127.0.0.1:8000/health/ready > /dev/null; then break; fi
  sleep 1
done
curl --max-time 10 -fsS http://127.0.0.1:8000/health | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"]=="7f466d0b34e0f52a64058d64d6406b7132bca775"'
curl --max-time 10 -fsS http://127.0.0.1:8000/health/ready
curl --max-time 10 -fsS http://127.0.0.1:8000/api/v1/auth/config
code_status=$(curl --max-time 10 -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/auth/me)
test "$code_status" = 401
curl --max-time 10 -fsS -o /dev/null http://127.0.0.1:8000/api/v1/products
docker inspect yance-prod-api-1 yance-prod-agent-worker-1 --format '{{.Name}} {{.Config.Image}} {{.State.Status}}'
docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'SELECT version_num FROM alembic_version;'
touch "$release/activated.ok"
echo RELEASE_ACTIVATED
date -u +%FT%TZ
