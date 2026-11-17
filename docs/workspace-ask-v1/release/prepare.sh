#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/workspace-20261117-01
b=/opt/yance/backups/workspace-20261117-01
test ! -e "$r"
install -d -m 755 "$r"
install -d -m 700 "$b"
tar -xzf /home/ubuntu/yance-workspace-release.tar.gz -C "$r"
old=$(readlink -f /opt/yance/website)
printf '%s' "$old" > "$b/website-path.txt"
cp -a /etc/systemd/system/yance-website.service.d "$b/dropins"
python3 - "$r" "$b" <<'PY'
import json,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
r,b=map(Path,sys.argv[1:]);services={};old={}
for service in ['api','agent-worker','payment-expiry','payment-reconcile']:
 c=json.loads(subprocess.check_output(['docker','inspect','yance-prod-'+service+'-1']))[0]
 env=dict(x.split('=',1) for x in c['Config']['Env']);old[service]={'image':c['Image'],'environment':env.copy()}
 env.update(APP_VERSION='workspace-20261117-01',APP_SOURCE_REVISION=(r/'SOURCE_REVISION').read_text().strip(),WORKSPACE_ASK_ENABLED='false')
 services[service]={'image':'yance-backend:workspace-20261117-01','environment':env}
(b/'rollback.override.json').write_text(json.dumps({'services':old}))
(r/'release.override.json').write_text(json.dumps({'services':services}))
subprocess.run(['docker','tag',old['api']['image'],'yance-backend:workspace-base-20261117'],check=True)
df='FROM yance-backend:workspace-base-20261117\n'
for name in json.loads((r/'PATCH_FILES.json').read_text()):
 assert name.startswith('yance-ai/') and '..' not in name
 df+='COPY --chown=yance:yance '+name+' /app/'+name.removeprefix('yance-ai/')+'\n'
(r/'Dockerfile').write_text(df)
env=services['api']['environment'].copy()
def save(name,env):
 assert not any('\n' in v for v in env.values())
 (r/name).write_text('\n'.join(k+'='+v for k,v in env.items())+'\n')
save('production.env',env)
u=urlsplit(env['DATABASE_URL']);env['DATABASE_URL']=urlunsplit((u.scheme,u.netloc,'/yance_workspace_1117_restore',u.query,u.fragment));env.update(EMAIL_ENABLED='false',SMS_ENABLED='false',POLICY_COLLECTION_ENABLED='false')
save('restore.env',env)
(r/'website/public/release.json').write_text(json.dumps({'release':'workspace-20261117-01','website_source':(r/'SOURCE_REVISION').read_text().strip(),'api_source':(r/'SOURCE_REVISION').read_text().strip(),'workspace_ask_enabled':False,'database_revision_at_release':'20261117_0043'}))
PY
docker build -t yance-backend:workspace-20261117-01 "$r" > "$r/backend-build.log" 2>&1
cmp "$old/package-lock.json" "$r/website/package-lock.json"
cp -a "$old/node_modules" "$r/website/node_modules"
cp "$old/.env.local" "$r/website/.env.local"
chmod 600 "$r/website/.env.local"
chown -R ubuntu:ubuntu "$r/website"
sudo -u ubuntu bash -c 'set -e; cd "$1"; npm run lint; npm run typecheck; npm run test:unit; API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r/website" > "$r/frontend-build.log" 2>&1
# Preserve old content-addressed assets in both directions for cached pages and rollback.
python3 "$r/copy_static.py" "$old/.next/standalone/.next/static" "$r/website/.next/standalone/.next/static"
tar --exclude='./.next/cache' -czf "$b/website.tar.gz" -C "$old" .
mkdir "$b/web-restore"
tar -xzf "$b/website.tar.gz" -C "$b/web-restore"
python3 - "$old" "$b/web-restore" <<'PY'
import hashlib,sys
from pathlib import Path
def hashes(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink() and not str(p.relative_to(root)).startswith('.next/cache/')}
assert hashes(Path(sys.argv[1]))==hashes(Path(sys.argv[2]))
PY
docker exec yance-prod-db-1 sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$b/database.dump"
docker exec yance-prod-db-1 sh -ec 'exec createdb -U "$POSTGRES_USER" yance_workspace_1117_restore'
docker exec -i yance-prod-db-1 sh -ec 'exec pg_restore -U "$POSTGRES_USER" -d yance_workspace_1117_restore --exit-on-error' < "$b/database.dump"
cp /opt/yance/releases/payment-20261113-01/check_database.py "$r/check_database.py"
chmod 644 "$r/check_database.py"
for stage in before after; do
 if [ "$stage" = after ]; then docker run --rm --network yance-prod_default --env-file "$r/restore.env" --entrypoint alembic yance-backend:workspace-20261117-01 upgrade head > "$r/restore-migration.log" 2>&1; fi
 docker run --rm --network yance-prod_default --env-file "$r/restore.env" -v "$r/check_database.py:/tmp/check_database.py:ro" --entrypoint python yance-backend:workspace-20261117-01 /tmp/check_database.py > "$r/restore-$stage.jsonl"
done
cmp "$r/restore-before.jsonl" "$r/restore-after.jsonl"
docker run --rm --network yance-prod_default --env-file "$r/restore.env" -v "$r/check_database.py:/tmp/check_database.py:ro" --entrypoint python yance-backend:workspace-base-20261117 /tmp/check_database.py > "$r/old-app-restored-new-db.jsonl"
cmp "$r/restore-after.jsonl" "$r/old-app-restored-new-db.jsonl"
docker run -d --name yance-workspace-candidate-api --network yance-prod_default --env-file "$r/restore.env" -p 127.0.0.1:8037:8000 yance-backend:workspace-20261117-01 > "$r/candidate-id.txt"
# Actual runtime image scan, preserving original application dependencies.
docker save yance-backend:workspace-20261117-01 -o "$r/image.tar"
docker run --rm -v "$r/image.tar:/scan/image.tar:ro" -v /opt/yance/releases/payment-20261113-01/trivy-cache:/root/.cache/trivy aquasec/trivy:0.70.0 image --input /scan/image.tar --timeout 10m --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --format json > "$r/scan.json" 2> "$r/scan.stderr"
rm "$r/image.tar"
docker image inspect -f '{{.Id}}' yance-backend:workspace-20261117-01 > "$r/approved-image.txt"
echo WORKSPACE_BACKUPS_RESTORED_MIGRATION_AND_OLD_APP_COMPATIBILITY_PASSED
