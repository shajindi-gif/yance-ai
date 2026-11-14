#!/usr/bin/env bash
# Run as root on the verified production host, only for this fixed release.
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/payment-20261113-01
b=/opt/yance/backups/payment-20261113-01
[ ! -e "$r" ]
sha256sum -c /home/ubuntu/yance-payment.sha256
install -d -m 755 "$r"
install -d -m 700 "$b"
tar -xzf /home/ubuntu/yance-payment.tar.gz -C "$r"
old=$(readlink -f /opt/yance/website)
[ "$old" = /opt/yance/releases/frontend-20261110-01/website ]
printf '%s\n' "$old" > "$b/website-path.txt"
cp -a /etc/systemd/system/yance-website.service.d "$b/dropins"
docker inspect -f '{{.Image}}' yance-prod-api-1 > "$b/api-image.txt"
docker inspect -f '{{.Image}}' yance-prod-agent-worker-1 > "$b/worker-image.txt"
tar --exclude='./.next/cache' -czf "$b/website.tar.gz" -C "$old" .
mkdir "$b/web-restore"
tar -xzf "$b/website.tar.gz" -C "$b/web-restore"
python3 - "$old" "$b/web-restore" <<'PY'
import hashlib,sys
from pathlib import Path
def hashes(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink() and not str(p.relative_to(root)).startswith('.next/cache/')}
assert hashes(sys.argv[1])==hashes(sys.argv[2])
print('WEBSITE_BACKUP_RESTORE_HASHES_PASSED')
PY
docker exec yance-prod-db-1 sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$b/database.dump"
test -s "$b/database.dump"
docker exec yance-prod-db-1 sh -ec 'exec createdb -U "$POSTGRES_USER" yance_payment_1113_restore'
docker exec -i yance-prod-db-1 sh -ec 'exec pg_restore -U "$POSTGRES_USER" -d yance_payment_1113_restore --exit-on-error' < "$b/database.dump"
python3 - "$r" "$b" <<'PY'
import json,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
r,b=map(Path,sys.argv[1:])
services={}; rollback={}
for service,container in [('api','yance-prod-api-1'),('agent-worker','yance-prod-agent-worker-1')]:
 c=json.loads(subprocess.check_output(['docker','inspect',container]))[0]
 env=dict(item.split('=',1) for item in c['Config']['Env'])
 rollback[service]={'image':c['Image'],'environment':env.copy()}
 env.update(APP_VERSION='payment-20261113-01',APP_SOURCE_REVISION=(r/'SOURCE_REVISION').read_text().strip())
 services[service]={'image':'yance-backend:payment-20261113-01','environment':env}
original=services['api']['environment'].copy()
(b/'rollback.override.json').write_text(json.dumps({'services':rollback}))
(r/'release.override.json').write_text(json.dumps({'services':services}))
# Private files stay on this host. Public scripts contain no credentials.
def write_env(name,env):
 assert not any('\n' in v for v in env.values()), 'Multiline env requires structured compose handling'
 (r/name).write_text('\n'.join(k+'='+v for k,v in env.items())+'\n')
write_env('production.env',original)
u=urlsplit(original['DATABASE_URL'])
restore=original.copy();restore['DATABASE_URL']=urlunsplit((u.scheme,u.netloc,'/yance_payment_1113_restore',u.query,u.fragment))
write_env('restore.env',restore)
# Only synthetic data and no external credentials in the candidate API.
testenv={k:v for k,v in original.items() if not k.startswith(('ALIPAY_','WXPAY_','OSS_','SMTP_','TENCENT_','OPENAI_','ANTHROPIC_','DASHSCOPE_','STRIPE_'))}
testenv.update(APP_ENV='test',DATABASE_URL=urlunsplit((u.scheme,u.netloc,'/yance_payment_1113_test',u.query,u.fragment)),EMAIL_ENABLED='false',SMS_ENABLED='false',LLM_DEFAULT_PROVIDER='mock',POLICY_COLLECTION_ENABLED='false',JWT_SECRET='synthetic-candidate-jwt-key-at-least-32-characters',API_KEY_PEPPER='synthetic-candidate-pepper-at-least-32-characters',BOOTSTRAP_TOKEN='synthetic-bootstrap-token',TENANT_PROVISIONING_TOKEN='synthetic-provisioning-token',PAYMENT_OPS_USER_ID='')
write_env('candidate.env',testenv)
base='yance-backend:payment-20261113-base'
subprocess.run(['docker','tag',rollback['api']['image'],base],check=True)
paths=json.loads((r/'PATCH_FILES.json').read_text())
assert 'yance-ai/app/services/policy_collection/scheduler.py' not in paths
dockerfile='FROM '+base+'\nENV PYTHONPATH=/app\n'
for path in paths:
 assert path.startswith('yance-ai/') and '..' not in path
 dockerfile+='COPY --chown=yance:yance '+path+' /app/'+path.removeprefix('yance-ai/')+'\n'
(r/'Dockerfile.patch').write_text(dockerfile)
(r/'website/public/release.json').write_text(json.dumps({'release':'payment-20261113-01','website_source':(r/'SOURCE_REVISION').read_text().strip(),'api_patch_source':(r/'SOURCE_REVISION').read_text().strip(),'preserved_module':'production policy collection scheduler','database_revision_at_release':'20261113_0042','runtime_version_url':'/api/runtime-version'}))
PY
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
