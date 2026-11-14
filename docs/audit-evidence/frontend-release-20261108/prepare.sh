#!/bin/bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/frontend-20261108-02
b=/opt/yance/backups/frontend-20261108-02
[ ! -e "$r" ]
[ "$(sha256sum /home/ubuntu/yance-depth.tar.gz | cut -d' ' -f1)" = af535a3a3de63adbfd2edf8fbc966e2453743688ad5478a9392235709dc25d31 ]
old=$(readlink -f /opt/yance/website)
[ "$old" = /opt/yance/releases/commercial-20261108-01/website ]
install -d -m 755 "$r"
install -d -m 700 "$b"
printf '%s\n' "$old" > "$b/website-path.txt"
cp -a /etc/systemd/system/yance-website.service.d "$b/dropins"
tar --exclude='./.next/cache' -czf "$b/website.tar.gz" -C "$old" .
mkdir "$b/restore"
tar -xzf "$b/website.tar.gz" -C "$b/restore"
python3 - "$old" "$b/restore" <<'PY'
import hashlib,sys
from pathlib import Path
def hashes(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink() and not str(p.relative_to(root)).startswith('.next/cache/')}
assert hashes(sys.argv[1])==hashes(sys.argv[2])
print('OLD_WEB_BACKUP_RESTORE_HASHES_PASSED')
PY
tar -xzf /home/ubuntu/yance-depth.tar.gz -C "$r"
cmp "$old/package-lock.json" "$r/website/package-lock.json"
cp -a "$old/node_modules" "$r/website/node_modules"
cp "$old/.env.local" "$r/website/.env.local"
chmod 600 "$r/website/.env.local"
python3 - "$r/website/public/release.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);p.write_text(json.dumps({'release':'frontend-20261108-02','website_source':'faf50b6','api_patch_source':'68b3d5b','runtime_version_url':'/api/runtime-version','scope':'frontend-only'}))
PY
cd "$r/website"
export NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:8000
npm run lint > "$r/lint.log" 2>&1
npm run typecheck > "$r/typecheck.log" 2>&1
npm run test:unit > "$r/unit.log" 2>&1
npm run build > "$r/build.log" 2>&1
# Preserve content-addressed assets for old cached HTML and rollback.
cp -an "$old/.next/standalone/.next/static/." "$r/website/.next/standalone/.next/static/"
systemd-run --unit=yance-depth-candidate --property="WorkingDirectory=$r/website" --setenv=NODE_ENV=production --setenv=HOSTNAME=127.0.0.1 --setenv=PORT=3028 --setenv=API_PROXY_TARGET=http://127.0.0.1:8000 /usr/bin/node "$r/website/.next/standalone/server.js"
sleep 2
curl -fsS http://127.0.0.1:3028/release.json | grep -q faf50b6
for path in / /pricing /login /discover /orders /applications /security; do curl -fsS -o /dev/null "http://127.0.0.1:3028$path"; done
printf 'CANDIDATE_BUILD_AND_SEVEN_PAGES_PASSED\n'
