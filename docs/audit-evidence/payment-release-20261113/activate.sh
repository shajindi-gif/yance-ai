#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/payment-20261113-01
b=/opt/yance/backups/payment-20261113-01
base=/opt/yance/releases/sms-20261029-01/yance-ai
grep -q PREPARED_BACKUP_RESTORED_MIGRATION_REPLAYED_CANDIDATE_BUILT /home/ubuntu/yance-payment-prepare.log
grep -q CANDIDATE_PG16_CONTRACTS_AND_WEB_PASSED "$r/approved.txt"
test "$(readlink -f /opt/yance/website)" = "$(cat "$b/website-path.txt")"
test "$(docker inspect -f '{{.Image}}' yance-prod-api-1)" = "$(cat "$b/api-image.txt")"
dc=(docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f /opt/yance/releases/commercial-20261108-01/api.override.json -f /opt/yance/releases/commercial-20261108-01/quality.override.json)
trap 'bash "$r/rollback.sh"' ERR
# Additive DDL was rehearsed against the restored production database. Old API
# remains compatible during this short migration; no financial data is rewritten.
docker run --rm --network yance-prod_default --env-file "$r/production.env" --entrypoint alembic yance-backend:payment-20261113-01 upgrade head > "$r/production-migration.log" 2>&1
"${dc[@]}" -f "$r/release.override.json" stop --timeout 120 agent-worker
"${dc[@]}" -f "$r/release.override.json" up -d --no-deps --no-build api agent-worker
python3 - "$r" <<'PY'
import json,sys,time,urllib.request
from pathlib import Path
revision=(Path(sys.argv[1])/'SOURCE_REVISION').read_text().strip()
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/system/version',timeout=3) as f:v=json.load(f)
  assert v['source_revision']==revision and v['database_revisions']==['20261113_0042']
  break
 except Exception:time.sleep(1)
else:raise SystemExit('API verification failed')
PY
old=$(cat "$b/website-path.txt")
cp -an "$r/website/.next/standalone/.next/static/." "$old/.next/standalone/.next/static/"
cat > /etc/systemd/system/yance-website.service.d/zzzzzz-payment-20261113.conf <<CONF
[Service]
WorkingDirectory=$r/website
ExecStart=
ExecStart=/usr/bin/node $r/website/.next/standalone/server.js
Environment=NODE_ENV=production
Environment=HOSTNAME=127.0.0.1
Environment=PORT=3000
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
CONF
ln -sfn "$r/website" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
python3 - "$r" <<'PY'
import json,sys,time,urllib.request
from pathlib import Path
revision=(Path(sys.argv[1])/'SOURCE_REVISION').read_text().strip()
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/api/runtime-version',timeout=5) as f:v=json.load(f)
  assert v['source_revision']==revision and v['database_revisions']==['20261113_0042']
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Web/API verification failed')
for path in ['/','/login','/pricing','/discover','/orders','/billing','/checkout','/success','/security']:
 with urllib.request.urlopen('http://127.0.0.1:3000'+path,timeout=15) as f:assert f.status==200
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=5) as f:c=json.load(f)
assert c['email_login_enabled'] and c['sms_login_enabled']
print('WEB_API_IDENTITY_PUBLIC_PAGES_AND_AUTH_ENTRANCES_PASSED')
PY
python3 - "$r" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);env=json.loads((r/'release.override.json').read_text())['services']['api']['environment'].copy()
# No customer messages are emitted while the nominated account is unregistered.
env.update(EMAIL_ENABLED='false',SMS_ENABLED='false',PAYMENT_OPS_USER_ID='',POLICY_COLLECTION_ENABLED='false')
services={}
for service,module,args in [('payment-expiry','payment_expiry',[]),('payment-reconcile','reconcile',['--daemon'])]:
 services[service]={'image':'yance-backend:payment-20261113-01','environment':env,'command':['python','-m','app.workers.'+module,*args],'restart':'unless-stopped','stop_grace_period':'60s','healthcheck':{'test':['CMD','python','-c',"import sys; sys.exit(0 if 'app.workers."+module+"' in open('/proc/1/cmdline','rb').read().decode() else 1)"],'interval':'30s','timeout':'5s','retries':3,'start_period':'15s'}}
(r/'workers.override.json').write_text(json.dumps({'services':services}))
PY
"${dc[@]}" -f "$r/release.override.json" -f "$r/workers.override.json" up -d --no-deps --no-build payment-expiry payment-reconcile
trap - ERR
echo PAYMENT_RELEASE_ACTIVE_DB0042_NO_REAL_TRANSACTION_TEST
