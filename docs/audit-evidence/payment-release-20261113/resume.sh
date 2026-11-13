#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/payment-20261113-01
b=/opt/yance/backups/payment-20261113-01
docker tag "$(cat "$b/api-image.txt")" yance-backend:payment-20261113-base
python3 - "$r/Dockerfile.patch" <<'PYTHON'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text().splitlines();s[0]='FROM yance-backend:payment-20261113-base';p.write_text('\n'.join(s)+'\n')
PYTHON
old=$(cat "$b/website-path.txt")
docker build -f "$r/Dockerfile.patch" -t yance-backend:payment-20261113-01 "$r" > "$r/backend-build.log" 2>&1
# Check original fields of restored financial and delivery rows before/after migration.
docker run --rm --network yance-prod_default --env-file "$r/restore.env" -v "$r/check_database.py:/tmp/check_database.py:ro" --entrypoint python yance-backend:payment-20261113-01 /tmp/check_database.py write > "$r/restore-baseline.log"
docker run --rm --network yance-prod_default --env-file "$r/restore.env" --entrypoint alembic yance-backend:payment-20261113-01 upgrade head > "$r/restore-migration.log" 2>&1
docker run --rm --network yance-prod_default --env-file "$r/restore.env" -v "$r/check_database.py:/tmp/check_database.py:ro" --entrypoint python yance-backend:payment-20261113-01 /tmp/check_database.py write > "$r/restore-after.log"
cmp "$r/restore-baseline.log" "$r/restore-after.log"
echo RESTORED_FINANCIAL_AND_DELIVERY_DATA_UNCHANGED
docker exec yance-prod-db-1 sh -ec 'exec createdb -U "$POSTGRES_USER" yance_payment_1113_test'
docker run --rm --network yance-prod_default --env-file "$r/candidate.env" --entrypoint alembic yance-backend:payment-20261113-01 upgrade head > "$r/candidate-migration.log" 2>&1
docker run --rm --network yance-prod_default --env-file "$r/candidate.env" --entrypoint alembic yance-backend:payment-20261113-01 downgrade -1 >> "$r/candidate-migration.log" 2>&1
docker run --rm --network yance-prod_default --env-file "$r/candidate.env" --entrypoint alembic yance-backend:payment-20261113-01 upgrade head >> "$r/candidate-migration.log" 2>&1
docker run -d --name yance-payment-candidate-api --network yance-prod_default --env-file "$r/candidate.env" -p 127.0.0.1:18013:8000 --entrypoint uvicorn yance-backend:payment-20261113-01 app.main:app --host 0.0.0.0 --port 8000 > "$r/candidate-container.txt"
cmp "$old/package-lock.json" "$r/website/package-lock.json"
cp -a "$old/node_modules" "$r/website/node_modules"
cp "$old/.env.local" "$r/website/.env.local"
chmod 600 "$r/website/.env.local"
chown -R ubuntu:ubuntu "$r/website"
sudo -u ubuntu bash -c 'set -e; cd "$1"; npm run lint; npm run typecheck; npm run test:unit; API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r/website" > "$r/frontend-build.log" 2>&1
cp -an "$old/.next/standalone/.next/static/." "$r/website/.next/standalone/.next/static/"
chmod 644 "$r/website/public/release.json"
systemd-run --uid=ubuntu --unit=yance-payment-candidate-web --property="WorkingDirectory=$r/website" --setenv=NODE_ENV=production --setenv=HOSTNAME=127.0.0.1 --setenv=PORT=3033 --setenv=API_PROXY_TARGET=http://127.0.0.1:8000 /usr/bin/node "$r/website/.next/standalone/server.js"
echo PREPARED_BACKUP_RESTORED_MIGRATION_REPLAYED_CANDIDATE_BUILT
