#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
release=/opt/yance/releases/full-20261028-01
backup=/opt/yance/backups/full-20261028-01/preflight
image=yance-backend:full-20261028-01
python3 "$release/ops/recovery.py" backup "$backup" > "$release/recovery-preflight.json"
recovery=yance-recovery-preflight
isolated=(docker run --rm --network "container:$recovery" --memory 512m --pids-limit 150
  -e APP_ENV=test -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_release_test
  -e EMAIL_ENABLED=false -e LLM_DEFAULT_PROVIDER=mock
  -e 'PGOPTIONS=-c lock_timeout=5000 -c statement_timeout=30000')
"${isolated[@]}" "$image" alembic upgrade 20261027_0033 > "$release/rehearsal-migration.log" 2>&1
"${isolated[@]}" "$image" alembic check >> "$release/rehearsal-migration.log" 2>&1
python3 "$release/ops/recovery.py" verify "$backup" "$recovery" yance_release_test > "$release/rehearsal-preservation.json"
# Run shutdown checks on a different, EMPTY synthetic database, never the customer snapshot.
docker exec "$recovery" createdb -U yance yance_shutdown_test
synthetic=(docker run --rm --network "container:$recovery" --memory 512m --pids-limit 150
  -e APP_ENV=test -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_shutdown_test
  -e YANCE_TEST_DATABASE_ACK=yance_shutdown_test -e EMAIL_ENABLED=false -e LLM_DEFAULT_PROVIDER=mock)
"${synthetic[@]}" "$image" alembic upgrade head > "$release/synthetic-migration.log" 2>&1
"${synthetic[@]}" "$image" python scripts/verify_worker_shutdown.py > "$release/worker-shutdown.json" 2>&1
docker stop "$recovery" > /dev/null
printf 'PREFLIGHT_RESTORED_MIGRATED_PRESERVED_WORKER_SHUTDOWN_VERIFIED\n'
