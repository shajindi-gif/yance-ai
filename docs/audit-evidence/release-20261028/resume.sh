#!/usr/bin/env bash
# Resume only the specifically approved frozen release, retaining all failed evidence.
set -Eeuo pipefail
umask 077
release=/opt/yance/releases/full-20261028-01
backup=/opt/yance/backups/full-20261028-01
expected=bd0ef295f186de9b76263cf00483724650f6bb8c
test "${1:-}" = approve-full-20261028-01-with-legacy-schema-exception
test "$(cat "$release/source-commit.txt")" = "$expected"
test "$(docker image inspect yance-backend:full-20261028-01 --format '{{.Id}}')" = "$(cat "$release/backend-image-id.txt")"
test "$(systemctl show yance-website -p WorkingDirectory --value)" = /opt/yance/releases/website-restore-full-20261028-01
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'SELECT version_num FROM alembic_version;')" = 20261020_0027
test "$(docker inspect yance-prod-api-1 --format '{{.State.Running}}')" = false
test "$(docker inspect yance-prod-agent-worker-1 --format '{{.State.Running}}')" = false
test -f "$backup/website/website-before.sha256"
python3 - "$release" <<'PYCONF'
from pathlib import Path
import json,re,sys
r=Path(sys.argv[1]); old=Path('/opt/yance/releases/backend-e58a7c4/yance-ai')
a=(old/'.env.prod').read_text(); b=(r/'yance-ai/.env.prod').read_text()
strip=lambda s:re.sub(r'^APP_VERSION=.*\n?', '',s,flags=re.M).strip()
assert strip(a)==strip(b), 'Private configuration unexpectedly changed'
assert re.findall(r'^APP_VERSION=(.*)$',b,re.M)==['bd0ef295f186de9b76263cf00483724650f6bb8c']
assert json.loads((r/'rehearsal-preservation.json').read_text())['verified']
for name in ['legacy-baseline-drift.json','legacy-migrated-drift.json']:
 result=json.loads((r/name).read_text().splitlines()[-1]); assert result['baseline_exception_verified']
assert json.loads((r/'candidate-readonly-checks.log').read_text().splitlines()[-1])['legacy_unowned_rows_excluded_for_two_transient_tenants']
assert '\"sigterm_passed\": true' in (r/'worker-shutdown.json').read_text()
print('Fixed image, unchanged secrets/configuration and approved evidence verified')
PYCONF
compose=(docker compose -p yance-prod --env-file "$release/yance-ai/.env.prod" -f "$release/yance-ai/docker-compose.prod.yml" -f "$release/yance-ai/release.override.yml")
test -s "$release/catalogue.json"
maintenance() {
  docker stop -t 30 yance-prod-api-1 yance-prod-agent-worker-1 > /dev/null 2>&1 || true
  if ! docker ps --format '{{.Names}}' | grep -qx yance-full-20261028-maintenance; then
    docker start yance-full-20261028-maintenance > /dev/null 2>&1 || \
    docker run -d --name yance-full-20261028-maintenance --restart unless-stopped --memory 96m -p 127.0.0.1:8000:8000 -v "$release/ops/maintenance.py:/maintenance.py:ro" -v "$release/catalogue.json:/catalogue.json:ro" --entrypoint python yance-backend:full-20261028-01 /maintenance.py > /dev/null
  fi
}
fallback() {
  result=$?
  trap - ERR
  maintenance
  bash "$release/ops/rollback-website.sh" || true
  echo 'RELEASE_FAILED_CLOSED: website fallback; API maintenance; schema and ledgers retained'
  exit "$result"
}
trap fallback ERR
# Prevent new API enqueues before draining/stopping the old worker. No mixed workers.
docker stop -t 150 yance-prod-api-1 > /dev/null
docker stop -t 150 yance-prod-agent-worker-1 > /dev/null
maintenance
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc "select count(*) from agent_runs where status='queued' or (status in ('planning','running') and lease_expires_at is not null);")" = 0
# Fresh final frozen snapshot, distinct from preflight. Failure leaves maintenance.
docker stop yance-recovery-final > /dev/null
python3 "$release/ops/recovery.py" backup "$backup/final-retry" > "$release/recovery-final-retry.json"
isolated=(docker run --rm --network container:yance-recovery-final-retry --memory 512m --pids-limit 150
 -e APP_ENV=test -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_release_test
 -e EMAIL_ENABLED=false -e LLM_DEFAULT_PROVIDER=mock -e 'PGOPTIONS=-c lock_timeout=5000 -c statement_timeout=30000')
"${isolated[@]}" yance-backend:full-20261028-01 alembic upgrade head > "$release/final-retry-clone-migration.log" 2>&1
python3 "$release/ops/recovery.py" verify "$backup/final-retry" yance-recovery-final-retry yance_release_test > "$release/final-retry-clone-preservation.json"
"${isolated[@]}" -v "$release/ops/verify-candidate.py:/verify.py:ro" yance-backend:full-20261028-01 python /verify.py > "$release/final-retry-candidate-checks.log" 2>&1
"${compose[@]}" run --rm --no-deps -e 'PGOPTIONS=-c lock_timeout=5000 -c statement_timeout=30000' migrate > "$release/production-migration.log" 2>&1
python3 "$release/ops/recovery.py" verify "$backup/final-retry" yance-prod-db-1 yance_prod > "$release/production-preservation.json"
docker stop yance-full-20261028-maintenance > /dev/null
"${compose[@]}" up -d --no-deps --no-build api
python3 - "$expected" <<'PY'
import json,sys,time,urllib.request
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3) as r:
   assert json.load(r)['version']==sys.argv[1]
  with urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=3) as r:
   assert json.load(r)['database']=='ok'
  break
 except Exception: time.sleep(1)
else: raise SystemExit('Candidate API failed to become ready')
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=10) as r:
 config=json.load(r); assert config['feedback_revision']==1 and config['application_workspace_revision']==2
PY
"${compose[@]}" up -d --no-deps --no-build agent-worker
cp -an /opt/yance/releases/website-web-20261026-01/website/.next/static/. "$release/website/.next/static/"
cp -an "$release/website/.next/static/." /opt/yance/releases/website-restore-full-20261028-01/.next/static/
conf=/etc/systemd/system/yance-website.service.d/99-full-20261028-01.conf
cat > "$conf.tmp" <<CONFIG
[Service]
WorkingDirectory=$release/website
ExecStart=
ExecStart=/usr/bin/node $release/website/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Environment=NODE_ENV=production
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
CONFIG
chmod 644 "$conf.tmp"; mv "$conf.tmp" "$conf"
ln -sfn "$release/website" /opt/yance/website
ln -sfn "$release/yance-ai" /opt/yance/yance-ai
systemctl daemon-reload
systemctl restart yance-website
python3 - <<'PY'
import json,time,urllib.request
for _ in range(45):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=3) as r:
   assert json.load(r)['release']=='full-20261028-01'
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Candidate website failed to become ready')
for path in ['/','/pricing','/feedback','/login','/security','/api/v1/products','/api/v1/auth/config']:
 with urllib.request.urlopen('http://127.0.0.1:3000'+path,timeout=15) as r:
  assert r.status==200; r.read()
print('LOCAL_PRODUCTION_READ_ONLY_CHECKS_PASSED')
PY
trap - ERR
docker stop yance-recovery-final-retry > /dev/null
date -u +%FT%TZ
echo FULL_RELEASE_ACTIVATED_PENDING_PUBLIC_ACCEPTANCE
