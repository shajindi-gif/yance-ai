#!/usr/bin/env bash
set -Eeuo pipefail
old=/opt/yance/releases/backend-7f466d0/yance-ai
new=/opt/yance/releases/backend-e58a7c4/yance-ai
expected=e58a7c46d6ed296aa1854455b3f4a4d4940afc35
python3 - <<'PYCONFIG'
from pathlib import Path
import shutil,re
old=Path('/opt/yance/releases/backend-7f466d0/yance-ai')
new=Path('/opt/yance/releases/backend-e58a7c4/yance-ai')
for folder in ['app','alembic']:
 a={str(p.relative_to(old/folder)):p.read_bytes() for p in (old/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
 b={str(p.relative_to(new/folder)):p.read_bytes() for p in (new/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
 assert a==b, 'Runtime logic or schema unexpectedly changed'
s=(old/'.env.prod').read_text()
s=re.sub(r'^APP_VERSION=.*$', 'APP_VERSION=e58a7c46d6ed296aa1854455b3f4a4d4940afc35', s, flags=re.M)
p=new/'.env.prod'; p.write_text(s); p.chmod(0o600)
s=(old/'release.override.yml').read_text().replace('7f466d0b34e0f52a64058d64d6406b7132bca775','e58a7c46d6ed296aa1854455b3f4a4d4940afc35').replace('7f466d0','e58a7c4')
(new/'release.override.yml').write_text(s)
print('Same application/schema; private configuration preserved except version')
PYCONFIG
old_compose=(docker compose -p yance-prod --env-file "$old/.env.prod" -f "$old/docker-compose.prod.yml" -f "$old/release.override.yml")
new_compose=(docker compose -p yance-prod --env-file "$new/.env.prod" -f "$new/docker-compose.prod.yml" -f "$new/release.override.yml")
fallback() {
  result=$?
  echo 'Runtime update failed: restoring same-schema, same-authentication 7f466d0 runtime.'
  "${old_compose[@]}" up -d --no-deps --no-build --timeout 30 api agent-worker
  exit "$result"
}
trap fallback ERR
test "$(readlink /opt/yance/yance-ai)" = "$old"
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'SELECT version_num FROM alembic_version;')" = 20261020_0027
"${new_compose[@]}" up -d --no-deps --no-build --timeout 30 api agent-worker
for attempt in {1..60}; do
  if curl --max-time 2 -fsS http://127.0.0.1:8000/health/ready > /dev/null 2>&1; then break; fi
  sleep 1
done
curl --max-time 10 -fsS http://127.0.0.1:8000/health | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"]=="e58a7c46d6ed296aa1854455b3f4a4d4940afc35"'
curl --max-time 10 -fsS http://127.0.0.1:8000/health/ready
ln -sfn "$new" /opt/yance/yance-ai
for tag in yance-prod-api yance-prod-agent-worker yance-prod-migrate yance-prod-document-worker; do docker tag yance-backend:e58a7c4 "$tag"; done
cp /opt/yance/releases/backend-e58a7c4/website/Dockerfile /opt/yance/website/Dockerfile
docker image inspect yance-backend:e58a7c4 --format '{{.Id}}'
date -u +%FT%TZ
echo RUNTIME_PATCH_ACTIVATED
