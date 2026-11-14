#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/commercial-20261108-01
b=/opt/yance/backups/commercial-20261108-01
python3 - <<'PY'
from pathlib import Path
p=Path('/opt/yance/releases/commercial-20261108-01/candidate.env')
old=dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line)
env={'DATABASE_URL':old['DATABASE_URL'],'APP_ENV':'test','JWT_SECRET':'synthetic-release-verification-key-at-least-32','API_KEY_PEPPER':'synthetic-pepper-release-verification-32','EMAIL_ENABLED':'false','SMS_ENABLED':'false','LLM_DEFAULT_PROVIDER':'mock','POLICY_COLLECTION_ENABLED':'false','APP_SOURCE_REVISION':'68b3d5b'}
p.write_text('\n'.join(k+'='+v for k,v in env.items())+'\n')
PY
docker run --rm --network yance-prod_default --env-file "$r/candidate.env" --entrypoint alembic yance-backend:commercial-20261108-01 upgrade head > "$r/migration-test.log" 2>&1
docker run -d --name yance-release-api-1108 --network yance-prod_default --env-file "$r/candidate.env" -p 127.0.0.1:18008:8000 --entrypoint uvicorn yance-backend:commercial-20261108-01 app.main:app --host 0.0.0.0 --port 8000 > "$r/candidate-container.txt"
chown -R ubuntu:ubuntu "$r/website"
sudo -u ubuntu bash -c 'set -e; cd "$1"; npm ci; npm run lint; npm run typecheck; npm run test:unit; npm audit --omit=dev --audit-level=high; NODE_OPTIONS=--max-old-space-size=768 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r/website" > "$r/website-build.log" 2>&1
cp -an "$(cat "$b/website-path.txt")/.next/standalone/.next/static/." "$r/website/.next/standalone/.next/static/"
echo PREPARED_BACKUP_RESTORED_API_ISOLATED_WEB_BUILT
