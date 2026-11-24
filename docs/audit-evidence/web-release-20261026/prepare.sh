#!/usr/bin/env bash
set -euo pipefail
umask 077
release=/opt/yance/releases/website-web-20261026-01
archive=/home/ubuntu/yance-web-20261026-01.tar.gz
expected_sha=$1
source_commit=$2
[ ! -e "$release" ]
[ "$(sha256sum "$archive" | cut -d' ' -f1)" = "$expected_sha" ]
sudo -n install -d -o ubuntu -g ubuntu -m 755 "$release"
tar -xzf "$archive" -C "$release"
cp -a "$release/docs/audit-evidence/web-release-20261026" "$release/ops"
printf '%s\n' "$source_commit" > "$release/source-commit.txt"
printf '%s\n' "$expected_sha" > "$release/source-archive-sha256.txt"
cp /opt/yance/releases/website-web-20261025-01/website/.env.local "$release/website/.env.local"
chmod 600 "$release/website/.env.local"
cd "$release/website"
npm ci > "$release/install.log" 2>&1
npm run typecheck > "$release/typecheck.log" 2>&1
npm audit --omit=dev --audit-level=high --json > "$release/dependency-audit.json"
nice -n 10 env NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 npm run build > "$release/build.log" 2>&1
# Old sessions can continue requesting their content-addressed assets.
cp -an /opt/yance/releases/website-web-20261025-01/website/.next/static/. .next/static/
# The independently restored fallback can also serve new cached chunks after rollback.
cp -an .next/static/. /opt/yance/releases/website-restore-web-20261026-01/.next/static/
node --version
node -e 'console.log("Next",require("next/package.json").version)'
node -e 'const r=require("./public/release.json");if(r.release!=="web-20261026-01")process.exit(1);console.log(r)'
cat .next/BUILD_ID
printf '\nCANDIDATE_BUILD_READY\n'
