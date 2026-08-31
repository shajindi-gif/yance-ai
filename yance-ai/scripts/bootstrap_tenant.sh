#!/usr/bin/env sh
set -eu

: "${BOOTSTRAP_TOKEN:?Set BOOTSTRAP_TOKEN first}"
BASE_URL="${BASE_URL:-http://localhost}"

curl --fail --silent --show-error \
  -X POST "${BASE_URL}/api/v1/auth/bootstrap" \
  -H "Content-Type: application/json" \
  -H "X-Bootstrap-Token: ${BOOTSTRAP_TOKEN}" \
  --data-binary @- <<'JSON'
{
  "tenant_name": "Yance AI",
  "tenant_slug": "yance-ai",
  "owner_email": "REPLACE_OWNER_EMAIL",
  "owner_name": "Yance Owner",
  "owner_password": "REPLACE_WITH_STRONG_PASSWORD"
}
JSON
echo

