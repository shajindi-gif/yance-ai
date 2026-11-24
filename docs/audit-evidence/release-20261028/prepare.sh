#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
release=/opt/yance/releases/full-20261028-01
archive=/home/ubuntu/yance-full-20261028-01.tar.gz
expected_sha=$1
source_commit=$2
[[ "$source_commit" =~ ^[a-f0-9]{40}$ ]]
test ! -e "$release"
test "$(sha256sum "$archive" | cut -d' ' -f1)" = "$expected_sha"
sudo -n install -d -o ubuntu -g ubuntu -m 755 "$release"
tar -xzf "$archive" -C "$release"
printf '%s\n' "$source_commit" > "$release/source-commit.txt"
printf '%s\n' "$expected_sha" > "$release/source-archive-sha256.txt"
cp -a "$release/docs/audit-evidence/release-20261028" "$release/ops"
sudo -n docker build --memory 1g -t yance-backend:full-20261028-01 "$release/yance-ai" > "$release/backend-build.log" 2>&1
sudo -n docker image inspect yance-backend:full-20261028-01 --format '{{.Id}}' > "$release/backend-image-id.txt"
cp /opt/yance/releases/website-web-20261026-01/website/.env.local "$release/website/.env.local"
chmod 600 "$release/website/.env.local"
cd "$release/website"
npm ci > "$release/frontend-install.log" 2>&1
npm run typecheck > "$release/frontend-types.log" 2>&1
npm run test:unit > "$release/frontend-unit.log" 2>&1
npm audit --omit=dev --audit-level=high --json > "$release/frontend-dependency-audit.json"
nice -n 10 env NODE_OPTIONS=--max-old-space-size=768 NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 npm run build > "$release/frontend-build.log" 2>&1
node -e 'if(require("./public/release.json").release!=="full-20261028-01")process.exit(1)'
printf 'CANDIDATE_BUILD_READY\n'
