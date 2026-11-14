#!/usr/bin/env bash
set -euo pipefail
umask 077
release=/opt/yance/releases/website-rollback-web-20261025-01
archive=/home/ubuntu/yance-web-fallback-20261025.tar.gz
expected_sha=$1
[ ! -e "$release" ]
[ "$(sha256sum "$archive" | cut -d' ' -f1)" = "$expected_sha" ]
sudo -n install -d -o ubuntu -g ubuntu -m 755 "$release"
tar -xzf "$archive" -C "$release"
cp /opt/yance/releases/website-web-20261020-01/website/.env.local "$release/website/.env.local"
chmod 600 "$release/website/.env.local"
cd "$release/website"
npm ci > "$release/install.log" 2>&1
npm run typecheck > "$release/typecheck.log" 2>&1
npm audit --omit=dev --audit-level=high --json > "$release/dependency-audit.json"
nice -n 10 env NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 npm run build > "$release/build.log" 2>&1
[ "$(node -p 'require("next/package.json").version')" = 16.4.3 ]
cp -an /opt/yance/releases/website-web-20261020-01/website/.next/static/. .next/static/
cat .next/BUILD_ID
printf '\nPATCHED_OLD_UI_READY\n'
