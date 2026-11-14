#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/website-images-20261029-01
old=/opt/yance/releases/growth-20261029-01/website
archive=/home/ubuntu/yance-images-20261029.tar.gz
sha=$1; commit=$2
[[ "$commit" =~ ^[0-9a-f]{40}$ ]]
test ! -e "$r"
test "$(sha256sum "$archive" | cut -d' ' -f1)" = "$sha"
test "$(systemctl show yance-website -p WorkingDirectory --value)" = "$old"
install -d -o ubuntu -g ubuntu -m 755 "$r"
tar -xzf "$archive" -C "$r"
printf '%s\n' "$commit" > "$r/source-commit.txt"
cp -a "$r/docs/audit-evidence/images-release-20261029" "$r/ops"
cp -a "$old/.env.local" "$r/website/.env.local"
chown -R ubuntu:ubuntu "$r/website"
sudo -u ubuntu bash -c 'set -e; cd "$1/website"; npm ci; npm run typecheck; npm audit --omit=dev --audit-level=high; NODE_OPTIONS=--max-old-space-size=768 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r" > "$r/build.log" 2>&1
bash "$r/ops/backup.sh" > "$r/backup-verification.log" 2>&1
cp -an "$old/.next/static/." "$r/website/.next/static/"
cp -an "$r/website/.next/static/." "$old/.next/static/"
trap 'bash "$r/ops/rollback.sh"; exit 1' ERR
cat > /etc/systemd/system/yance-website.service.d/99-images-20261029-01.conf <<CONF
[Service]
WorkingDirectory=$r/website
ExecStart=
ExecStart=/usr/bin/node $r/website/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Environment=NODE_ENV=production
Environment=API_PROXY_TARGET=http://127.0.0.1:8000
CONF
ln -sfn "$r/website" /opt/yance/website
systemctl daemon-reload
systemctl restart yance-website
python3 - <<'PYREADY'
import json,time,urllib.request
for _ in range(45):
 try:
  with urllib.request.urlopen('http://127.0.0.1:3000/release.json',timeout=3) as r:assert json.load(r)['release']=='images-20261029-01'
  break
 except Exception:time.sleep(1)
else:raise SystemExit('Website readiness failed')
with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=10) as r:assert json.load(r)['version']=='4587e34251a1ebcd85c55ae706f1a82ceb25de2b'
print('NEW_WEBSITE_READY_BACKEND_UNCHANGED')
PYREADY
trap - ERR
date -u +%FT%TZ
