#!/usr/bin/env bash
# Continue after an explicitly recorded existing-schema check failure.
set -Eeuo pipefail
umask 077
release=/opt/yance/releases/full-20261028-01
recovery=yance-recovery-preflight
backup=/opt/yance/backups/full-20261028-01/preflight
docker start "$recovery" > /dev/null
for attempt in {1..30}; do
 if docker exec "$recovery" pg_isready -U yance -d yance_release_test > /dev/null 2>&1; then break; fi
 sleep 1
done
docker exec "$recovery" createdb -U yance yance_baseline_test
# Schema only: no new customer-data copy, and no production schema change.
docker exec yance-prod-db-1 pg_dump -U yance --schema-only --no-owner --no-acl yance_prod | docker exec -i "$recovery" psql -X -q -v ON_ERROR_STOP=1 -U yance -d yance_baseline_test > "$release/baseline-schema-restore.log" 2>&1
isolated=(docker run --rm --network "container:$recovery" --memory 512m --pids-limit 150 -e APP_ENV=test -e EMAIL_ENABLED=false -e LLM_DEFAULT_PROVIDER=mock)
"${isolated[@]}" -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_baseline_test -v "$release/ops/verify-legacy-drift.py:/verify.py:ro" yance-backend:e58a7c4 python /verify.py > "$release/legacy-baseline-drift.json" 2>&1
"${isolated[@]}" -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_release_test -v "$release/ops/verify-legacy-drift.py:/verify.py:ro" yance-backend:full-20261028-01 python /verify.py > "$release/legacy-migrated-drift.json" 2>&1
"${isolated[@]}" -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_release_test -v "$release/ops/verify-candidate.py:/verify.py:ro" yance-backend:full-20261028-01 python /verify.py > "$release/candidate-readonly-checks.log" 2>&1
python3 "$release/ops/recovery.py" verify "$backup" "$recovery" yance_release_test > "$release/rehearsal-preservation.json"
docker exec "$recovery" createdb -U yance yance_shutdown_test
synthetic=("${isolated[@]}" -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_shutdown_test -e YANCE_TEST_DATABASE_ACK=yance_shutdown_test)
"${synthetic[@]}" yance-backend:full-20261028-01 alembic upgrade head > "$release/synthetic-migration.log" 2>&1
"${synthetic[@]}" yance-backend:full-20261028-01 python scripts/verify_worker_shutdown.py > "$release/worker-shutdown.json" 2>&1
docker stop "$recovery" > /dev/null
echo PREFLIGHT_COMPLETED_WITH_EXPLICIT_LEGACY_SCHEMA_EXCEPTION
