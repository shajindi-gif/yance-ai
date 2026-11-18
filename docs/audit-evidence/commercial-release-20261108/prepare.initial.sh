#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/commercial-20261108-01
b=/opt/yance/backups/commercial-20261108-01
[ ! -e "$r" ]
[ "$(sha256sum /home/ubuntu/yance-commercial-1108.tar.gz | cut -d' ' -f1)" = 0baa247400f760b8ec8a5fd1d820c327a5ff5ce936c77b417cbf62954c445a05 ]
install -d -m 755 "$r"
install -d -m 700 "$b"
readlink -f /opt/yance/website > "$b/website-path.txt"
systemctl cat yance-website > "$b/website-service.txt"
cp -a /etc/systemd/system/yance-website.service.d "$b/website-dropins"
docker inspect -f '{{.Image}}' yance-prod-api-1 > "$b/api-image.txt"
docker inspect -f '{{.Config.Image}}' yance-prod-api-1 > "$b/api-tag.txt"
docker exec yance-prod-api-1 sha256sum /app/app/api/routes/health.py /app/app/api/routes/policies.py /app/app/services/policy_collection/keyword_search.py > "$b/api-files-before.txt"
grep -q '^8d734a67e478c44f743f4392ac9df90309b059bacc59ebb02b412ca5d18a0b07 ' "$b/api-files-before.txt"
grep -q '^d3d6cf2184f1a491e2d45218853fddf93a9ca1a852989a9891f1a4325150b7d1 ' "$b/api-files-before.txt"
grep -q '^fbcc3a9eb9a62f0fdf8465989b6dd77779d0671c2b620e7fa50a856f328fd10c ' "$b/api-files-before.txt"
docker exec yance-prod-db-1 sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$b/database.dump"
test -s "$b/database.dump"
docker exec yance-prod-db-1 sh -ec 'exec createdb -U "$POSTGRES_USER" yance_release_1108_restore'
docker exec -i yance-prod-db-1 sh -ec 'exec pg_restore -U "$POSTGRES_USER" -d yance_release_1108_restore --exit-on-error' < "$b/database.dump"
docker exec yance-prod-db-1 sh -ec 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select version_num from alembic_version; select count(*) from orders;"' > "$b/live-counts.txt"
docker exec yance-prod-db-1 sh -ec 'psql -U "$POSTGRES_USER" -d yance_release_1108_restore -Atc "select version_num from alembic_version; select count(*) from orders;"' > "$b/restored-counts.txt"
cmp "$b/live-counts.txt" "$b/restored-counts.txt"
grep -qx 20261106_0038 <(head -1 "$b/live-counts.txt")
oldweb=$(cat "$b/website-path.txt")
tar --exclude='./.next/cache' -czf "$b/website.tar.gz" -C "$oldweb" .
mkdir "$b/website-restore"
tar -xzf "$b/website.tar.gz" -C "$b/website-restore"
python3 - "$oldweb" "$b/website-restore" <<'PY'
import sys,hashlib
from pathlib import Path
def sums(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink() and not str(p.relative_to(root)).startswith('.next/cache/')}
assert sums(sys.argv[1])==sums(sys.argv[2])
print('WEBSITE_RESTORE_HASHES_VERIFIED')
PY
tar -xzf /home/ubuntu/yance-commercial-1108.tar.gz -C "$r"
cp "$oldweb/.env.local" "$r/website/.env.local"
chmod 600 "$r/website/.env.local"
python3 - "$r" "$b" <<'PY'
import json,subprocess,sys,os
from pathlib import Path
r,b=map(Path,sys.argv[1:]); c=json.loads(subprocess.check_output(['docker','inspect','yance-prod-api-1']))[0]
env=dict(item.split('=',1) for item in c['Config']['Env'])
image=c['Image']
(b/'rollback-api.json').write_text(json.dumps({'services':{'api':{'image':image,'environment':env}}}))
env.update(APP_VERSION='web-20261106-05+68b3d5b',APP_SOURCE_REVISION='68b3d5b')
(r/'api.override.json').write_text(json.dumps({'services':{'api':{'image':'yance-backend:commercial-20261108-01','environment':env}}}))
(r/'Dockerfile.patch').write_text('FROM '+c['Config']['Image']+'\nCOPY --chown=yance:yance yance-ai/app/api/routes/health.py /app/app/api/routes/health.py\nCOPY --chown=yance:yance yance-ai/app/api/routes/policies.py /app/app/api/routes/policies.py\nCOPY --chown=yance:yance yance-ai/app/services/policy_collection/keyword_search.py /app/app/services/policy_collection/keyword_search.py\n')
# The isolated API is disabled for all paid/outbound provider calls.
for k in list(env):
 if any(x in k for x in ['SECRET','API_KEY','PRIVATE_KEY','PASSWORD','ACCESS_KEY','TOKEN','WXPAY_','ALIPAY_','STRIPE_']): env[k]=''
from urllib.parse import urlsplit,urlunsplit
original=dict(item.split('=',1) for item in c['Config']['Env'])
u=urlsplit(original['DATABASE_URL']);env['DATABASE_URL']=urlunsplit((u.scheme,u.netloc,'/yance_release_1108_test',u.query,u.fragment))
env.update(APP_ENV='test',EMAIL_ENABLED='false',SMS_ENABLED='false',LLM_DEFAULT_PROVIDER='mock',POLICY_COLLECTION_ENABLED='false',JWT_SECRET='synthetic-release-verification-key-at-least-32',API_KEY_PEPPER='synthetic-pepper-release-verification-32')
(r/'candidate.env').write_text('\n'.join(k+'='+v for k,v in env.items())+'\n')
(r/'website/public/release.json').write_text(json.dumps({'release':'commercial-20261108-01','website_source':'68b3d5b','api_base_image':c['Config']['Image'],'api_patch_source':'68b3d5b','database_revision_at_release':'20261106_0038','runtime_version_url':'/api/runtime-version'}))
PY
chmod 600 "$r/api.override.json" "$r/candidate.env" "$b/rollback-api.json"
docker build -f "$r/Dockerfile.patch" -t yance-backend:commercial-20261108-01 "$r" > "$r/api-build.log" 2>&1
docker exec yance-prod-db-1 sh -ec 'exec createdb -U "$POSTGRES_USER" yance_release_1108_test'
docker run --rm --network yance-prod_default --env-file "$r/candidate.env" --entrypoint alembic yance-backend:commercial-20261108-01 upgrade head > "$r/migration-test.log" 2>&1
docker run -d --name yance-release-api-1108 --network yance-prod_default --env-file "$r/candidate.env" -p 127.0.0.1:18008:8000 --entrypoint uvicorn yance-backend:commercial-20261108-01 app.main:app --host 0.0.0.0 --port 8000 > "$r/candidate-container.txt"
chown -R ubuntu:ubuntu "$r/website"
sudo -u ubuntu bash -c 'set -e; cd "$1"; npm ci; npm run lint; npm run typecheck; npm run test:unit; npm audit --omit=dev --audit-level=high; NODE_OPTIONS=--max-old-space-size=768 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r/website" > "$r/website-build.log" 2>&1
cp -an "$oldweb/.next/standalone/.next/static/." "$r/website/.next/standalone/.next/static/"
echo PREPARED_BACKUP_RESTORED_API_ISOLATED_WEB_BUILT
