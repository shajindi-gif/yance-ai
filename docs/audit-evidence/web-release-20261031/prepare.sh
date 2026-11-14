#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/web-20261031-01
b=/opt/yance/backups/web-20261031-01
old=/opt/yance/releases/sms-20261029-01
[ "$(sha256sum /home/ubuntu/website-source.tar.gz | cut -d' ' -f1)" = 0fd6413b4088c2f5e91ae52d79c44e394deb9be71baac7ea849c3ff3992b3d4d ]
[ ! -e "$r" ]
install -d -o ubuntu -g ubuntu -m 755 "$r"
install -d -m 700 "$b"
systemctl cat yance-website > "$b/service-before.conf"
cp -a /etc/systemd/system/yance-website.service.d "$b/service-before"
readlink -f /opt/yance/website > "$b/website-path.txt"
docker inspect --format '{{.Image}}' yance-prod-api-1 > "$b/api-image.txt"
docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atqc 'select version_num from alembic_version' > "$b/db-revision.txt"
[ "$(cat "$b/db-revision.txt")" = 20261029_0034 ]
tar --exclude='./.next/cache' -czf "$b/website-before.tar.gz" -C "$old/website" .
mkdir "$b/website-restore"
tar -xzf "$b/website-before.tar.gz" -C "$b/website-restore"
python3 - "$old/website" "$b/website-restore" <<'PY'
import hashlib,json,sys
from pathlib import Path
def manifest(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink() and not str(p.relative_to(root)).startswith('.next/cache/')}
a,b=map(manifest,sys.argv[1:]);assert a==b
print(json.dumps({'backup_restore_equal':True,'files':len(a)}))
PY
tar -xzf /home/ubuntu/website-source.tar.gz -C "$r"
cp "$old/website/.env.local" "$r/website/.env.local"
chmod 600 "$r/website/.env.local"
printf '%s\n' '{"release":"web-20261031-01","source":"5bd9e19","backend":"b408a535+sms-consent-5bd9e19","migration":"20261029_0034"}' > "$r/website/public/release.json"
cp /home/ubuntu/sms_auth.py /home/ubuntu/Dockerfile.compat "$r/"
docker build -f "$r/Dockerfile.compat" -t yance-backend:web-auth-20261031-01 "$r" > "$r/backend-build.log" 2>&1
cat > "$r/compat.override.yml" <<'YML'
services:
  api:
    image: yance-backend:web-auth-20261031-01
    environment:
      APP_VERSION: b408a535+sms-consent-5bd9e19
YML
chown -R ubuntu:ubuntu "$r"
sudo -u ubuntu bash -c 'set -e; cd "$1/website"; npm ci; npm run lint; npm run typecheck; npm run test:unit; npm audit --omit=dev --audit-level=high; NODE_OPTIONS=--max-old-space-size=768 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r" > "$r/website-build.log" 2>&1
cp -an "$old/website/.next/static/." "$r/website/.next/standalone/.next/static/"
printf 'BACKUP_VERIFIED_CANDIDATE_BUILT_NOT_ACTIVE\n'
