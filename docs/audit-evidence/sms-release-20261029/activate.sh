#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/sms-20261029-01
b=/opt/yance/backups/sms-20261029-01
web=/opt/yance/releases/website-images-20261029-01/website
commit=$(cat "$r/source-commit.txt")
new=(docker compose -p yance-prod --env-file "$r/yance-ai/.env.prod" -f "$r/yance-ai/docker-compose.prod.yml" -f "$r/yance-ai/release.override.yml")
python3 - "$r" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1])
assert json.loads((r/'preflight-backup.json').read_text())['verified']
s=json.loads((r/'clone-preservation.json').read_text());assert s['verified'] and s['revision']=='20261029_0034'
assert 'OLD_USER_CONTRACT_READ_PASSED' in (r/'old-contract-check.txt').read_text()
PY
curl -fsS --max-time 15 http://127.0.0.1:8000/api/v1/products > "$r/catalogue.json"
# Stop enqueues first, allow in-flight workers to finish before the frozen snapshot.
trap 'bash "$r/ops/rollback.sh"; exit 1' ERR
docker stop -t 150 yance-prod-api-1 >/dev/null
docker stop -t 150 yance-prod-agent-worker-1 >/dev/null
docker run -d --name yance-sms-maintenance --restart unless-stopped --memory 96m -p 127.0.0.1:8000:8000 -v "$r/ops/maintenance.py:/maintenance.py:ro" -v "$r/catalogue.json:/catalogue.json:ro" --entrypoint python yance-backend:sms-20261029-01 /maintenance.py >/dev/null
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atqc "select count(*) from agent_runs where status='queued' or (status in ('planning','running') and lease_expires_at is not null);")" = 0
python3 "$r/ops/recovery.py" backup "$b/sms-final" > "$r/final-backup.json"
"${new[@]}" run --rm --no-deps -e 'PGOPTIONS=-c lock_timeout=5000 -c statement_timeout=30000' migrate > "$r/production-migration.log" 2>&1
python3 "$r/ops/recovery.py" verify "$b/sms-final" yance-prod-db-1 yance_prod > "$r/production-preservation.json"
docker stop yance-recovery-sms-final >/dev/null
docker stop yance-sms-maintenance >/dev/null
"${new[@]}" up -d --no-deps --no-build api agent-worker
python3 - "$commit" <<'PY'
import json,sys,time,urllib.request
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3) as r:assert json.load(r)['version']==sys.argv[1]
  with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=3) as r:assert json.load(r)['sms_login_enabled'] is False
  break
 except Exception:time.sleep(1)
else:raise SystemExit('API readiness failed')
PY
cp -an "$web/.next/static/." "$r/website/.next/static/"
cp -an "$r/website/.next/static/." "$web/.next/static/"
cat > /etc/systemd/system/yance-website.service.d/99-sms-20261029-01.conf <<CONF
[Service]
WorkingDirectory=$r/website
ExecStart=
ExecStart=/usr/bin/node $r/website/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Environment=NODE_ENV=production
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
CONF
ln -sfn "$r/website" /opt/yance/website;ln -sfn "$r/yance-ai" /opt/yance/yance-ai
systemctl daemon-reload;systemctl restart yance-website
python3 - <<'PY'
import json,time,urllib.request
for _ in range(45):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=3) as r:assert json.load(r)['release']=='sms-20261029-01'
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Website readiness failed')
PY
# Explicit final capability switch only after old-data preservation and both apps healthy.
python3 - "$r/yance-ai/.env.prod" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);s=p.read_text();assert len(re.findall(r'^SMS_ENABLED=false$',s,re.M))==1
p.write_text(re.sub(r'^SMS_ENABLED=false$', 'SMS_ENABLED=true',s,flags=re.M));p.chmod(0o600)
PY
"${new[@]}" up -d --no-deps --no-build api agent-worker
python3 - <<'PY'
import json,time,urllib.request
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=3) as r:
   c=json.load(r);assert c['sms_login_enabled'] is True and c['email_login_enabled'] is True
  break
 except Exception:time.sleep(1)
else:raise SystemExit('SMS readiness failed')
PY
trap - ERR
date -u +%FT%TZ
echo SMS_RELEASE_ACTIVE_PENDING_PUBLIC_BROWSER
