#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/growth-20261029-01
old=/opt/yance/releases/full-20261028-01
b=/opt/yance/backups/growth-20261029-01
sha=$1; commit=$2
[[ "$commit" =~ ^[a-f0-9]{40}$ ]]
test "$(sha256sum /home/ubuntu/yance-growth-20261029.tar.gz | cut -d' ' -f1)" = "$sha"
test ! -e "$r"
test "$(systemctl show yance-website -p WorkingDirectory --value)" = "$old/website"
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atc 'select version_num from alembic_version;')" = 20261027_0033
install -d -o ubuntu -g ubuntu -m 755 "$r"
tar -xzf /home/ubuntu/yance-growth-20261029.tar.gz -C "$r"
mkdir -p "$b"; chmod 700 "$b"
printf '%s\n' "$commit" > "$r/source-commit.txt"
cp -a "$r/docs/audit-evidence/growth-release-20261029" "$r/ops"
# Preserve all current secrets; only version metadata changes.
cp -a "$old/yance-ai/.env.prod" "$r/yance-ai/.env.prod"
cp -a "$old/website/.env.local" "$r/website/.env.local"
cp -a "$old/yance-ai/.env.prod" "$b/backend-env.private"
cp -a "$old/yance-ai/release.override.yml" "$b/backend-override.yml"
cp -a /etc/systemd/system/yance-website.service.d "$b/service-before"
python3 - "$r" "$commit" <<'PYCONF'
from pathlib import Path
import re,sys
r=Path(sys.argv[1]); commit=sys.argv[2];old=Path('/opt/yance/releases/full-20261028-01/yance-ai')
p=r/'yance-ai/.env.prod';s=p.read_text();assert len(re.findall(r'^APP_VERSION=',s,re.M))==1
p.write_text(re.sub(r'^APP_VERSION=.*$', 'APP_VERSION='+commit,s,flags=re.M));p.chmod(0o600)
s=(old/'release.override.yml').read_text().replace('bd0ef295f186de9b76263cf00483724650f6bb8c',commit).replace('full-20261028-01','growth-20261029-01')
(r/'yance-ai/release.override.yml').write_text(s)
PYCONF
docker build --memory 1g -t yance-backend:growth-20261029-01 "$r/yance-ai" > "$r/backend-build.log" 2>&1
chown -R ubuntu:ubuntu "$r/website"
sudo -u ubuntu bash -c 'set -e; cd "$1/website"; npm ci; npm run typecheck; npm run test:unit; npm audit --omit=dev --audit-level=high; NODE_OPTIONS=--max-old-space-size=768 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r" > "$r/website-build.log" 2>&1
# Verify a new database backup before touching running services. No migrations.
python3 "$r/ops/recovery.py" backup "$b/growth-preflight" > "$r/backup-verification.json"
docker stop yance-recovery-growth-preflight > /dev/null
tar --exclude='./.next/cache' -czf "$b/website-before.tar.gz" -C "$old/website" .
mkdir "$b/website-restore"; tar -xzf "$b/website-before.tar.gz" -C "$b/website-restore"
python3 - "$old/website" "$b/website-restore" <<'PYVERIFY'
import hashlib,sys
from pathlib import Path
def hashes(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink() and not str(p.relative_to(root)).startswith('.next/cache/')}
assert hashes(sys.argv[1])==hashes(sys.argv[2])
print('WEBSITE_BACKUP_RESTORE_MATCHED')
PYVERIFY
new=(docker compose -p yance-prod --env-file "$r/yance-ai/.env.prod" -f "$r/yance-ai/docker-compose.prod.yml" -f "$r/yance-ai/release.override.yml")
prev=(docker compose -p yance-prod --env-file "$old/yance-ai/.env.prod" -f "$old/yance-ai/docker-compose.prod.yml" -f "$old/yance-ai/release.override.yml")
rollback() {
 trap - ERR
 "${prev[@]}" up -d --no-deps --no-build api agent-worker
 rm -f /etc/systemd/system/yance-website.service.d/99-growth-20261029-01.conf
 ln -sfn "$old/website" /opt/yance/website; ln -sfn "$old/yance-ai" /opt/yance/yance-ai
 systemctl daemon-reload; systemctl restart yance-website
 echo ROLLED_BACK_APPLICATION_ONLY_DATABASE_UNCHANGED
}
trap 'rollback; exit 1' ERR
"${new[@]}" up -d --no-deps --no-build --timeout 60 api agent-worker
python3 - "$commit" <<'PYREADY'
import json,sys,time,urllib.request
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3) as r: assert json.load(r)['version']==sys.argv[1]
  with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/auth/config',timeout=3) as r: assert json.load(r)['checkout_idempotency_revision']==1
  break
 except Exception:time.sleep(1)
else:raise SystemExit('API readiness failed')
PYREADY
cp -an "$old/website/.next/static/." "$r/website/.next/static/"
cp -an "$r/website/.next/static/." "$old/website/.next/static/"
cat > /etc/systemd/system/yance-website.service.d/99-growth-20261029-01.conf <<CONF
[Service]
WorkingDirectory=$r/website
ExecStart=
ExecStart=/usr/bin/node $r/website/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Environment=NODE_ENV=production
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
CONF
ln -sfn "$r/website" /opt/yance/website; ln -sfn "$r/yance-ai" /opt/yance/yance-ai
systemctl daemon-reload; systemctl restart yance-website
python3 - <<'PYWEB'
import json,time,urllib.request
for _ in range(45):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=3) as r: assert json.load(r)['release']=='growth-20261029-01'
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Website readiness failed')
PYWEB
trap - ERR
date -u +%FT%TZ
echo GROWTH_RELEASE_ACTIVE_PENDING_PUBLIC_CHECK
