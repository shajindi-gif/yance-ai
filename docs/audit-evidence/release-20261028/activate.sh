#!/usr/bin/env bash
# Only execute after specific migration / maintenance / fallback acceptance.
set -Eeuo pipefail
umask 077
release=/opt/yance/releases/full-20261028-01
old=/opt/yance/releases/backend-e58a7c4/yance-ai
backup=/opt/yance/backups/full-20261028-01
expected=bd0ef295f186de9b76263cf00483724650f6bb8c
test "${1:-}" = approve-full-20261028-01-with-legacy-schema-exception
test "$(cat "$release/source-commit.txt")" = "$expected"
test "$(readlink -f /opt/yance/yance-ai)" = "$old"
test "$(systemctl show yance-website -p WorkingDirectory --value)" = /opt/yance/releases/website-web-20261026-01/website
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'SELECT version_num FROM alembic_version;')" = 20261020_0027
test -f "$backup/website/website-before.sha256"
python3 - "$release" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1])
assert json.loads((r/'recovery-preflight.json').read_text())['verified']
assert json.loads((r/'rehearsal-preservation.json').read_text())['verified']
for name in ['legacy-baseline-drift.json','legacy-migrated-drift.json']:
 # Tool logging can precede the one-line structured result.
 result=json.loads((r/name).read_text().splitlines()[-1])
 assert result['baseline_exception_verified'] and not result['standard_alembic_check_passed']
assert json.loads((r/'candidate-readonly-checks.log').read_text().splitlines()[-1])['legacy_unowned_rows_excluded_for_two_transient_tenants']
assert '"sigterm_passed": true' in (r/'worker-shutdown.json').read_text()
assert not json.loads((r/'frontend-dependency-audit.json').read_text())['metadata']['vulnerabilities']['high']
PY
systemctl cat yance-website | cmp -s - "$backup/website/service-before.conf"
cp -a "$old/.env.prod" "$backup/backend-env-before.private"
cp -a "$old/release.override.yml" "$backup/backend-override-before.yml"
tar --exclude='./.git' --exclude='./.venv' --exclude='./__pycache__' -czf "$backup/backend-before.tar.gz" -C "$old" .
sha256sum "$backup/backend-before.tar.gz" > "$backup/backend-before.sha256"
docker inspect yance-prod-api-1 --format '{{.Image}}' > "$backup/backend-image-before.txt"
python3 - "$old" "$release/yance-ai" "$expected" <<'PY'
from pathlib import Path
import re,sys
old,new,commit=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
s=(old/'.env.prod').read_text()
versions=re.findall(r'^APP_VERSION=(.*)$',s,re.M)
assert all(v.strip()=='e58a7c46d6ed296aa1854455b3f4a4d4940afc35' for v in versions), 'Unexpected existing version'
s=re.sub(r'^APP_VERSION=.*\n?', '',s,flags=re.M)
s=s.rstrip()+'\nAPP_VERSION='+commit+'\n'
(new/'.env.prod').write_text(s); (new/'.env.prod').chmod(0o600)
s=(old/'release.override.yml').read_text().replace('e58a7c46d6ed296aa1854455b3f4a4d4940afc35',commit).replace('e58a7c4','full-20261028-01')
before,worker=s.split('  agent-worker:\n',1)
worker=worker.replace('    environment:\n','    environment:\n      EMAIL_ENABLED: "false"\n',1)
(new/'release.override.yml').write_text(before+'  agent-worker:\n'+worker)
print('Existing secrets and API email configuration retained; worker outbound email disabled')
PY
compose=(docker compose -p yance-prod --env-file "$release/yance-ai/.env.prod" -f "$release/yance-ai/docker-compose.prod.yml" -f "$release/yance-ai/release.override.yml")
curl -fsS --max-time 15 http://127.0.0.1:8000/api/v1/products > "$release/catalogue.json"
chmod 644 "$release/catalogue.json"
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
python3 "$release/ops/recovery.py" backup "$backup/final" > "$release/recovery-final.json"
"${compose[@]}" run --rm --no-deps -e 'PGOPTIONS=-c lock_timeout=5000 -c statement_timeout=30000' migrate > "$release/production-migration.log" 2>&1
python3 "$release/ops/recovery.py" verify "$backup/final" yance-prod-db-1 yance_prod > "$release/production-preservation.json"
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
docker stop yance-recovery-final > /dev/null
date -u +%FT%TZ
echo FULL_RELEASE_ACTIVATED_PENDING_PUBLIC_ACCEPTANCE
