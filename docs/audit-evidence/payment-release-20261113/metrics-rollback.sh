#!/usr/bin/env bash
set -Eeuo pipefail
r=/opt/yance/releases/payment-metrics-20261115-02
base=/opt/yance/releases/sms-20261029-01/yance-ai
docker compose -p yance-prod --env-file "$base/.env.prod" -f "$base/docker-compose.prod.yml" -f "$base/release.override.yml" -f /opt/yance/releases/web-20261031-01/compat.override.yml -f /opt/yance/releases/commercial-20261108-01/api.override.json -f /opt/yance/releases/commercial-20261108-01/quality.override.json -f /opt/yance/releases/payment-20261113-01/release.override.json -f /opt/yance/releases/payment-20261113-01/workers.override.json -f "$r/rollback.override.json" up -d --no-deps --no-build api agent-worker payment-expiry payment-reconcile
python3 - "$r" <<'PY'
from pathlib import Path
import sys
r=Path(sys.argv[1]);web=Path((r/'website-path.txt').read_text())
for p in [web/'public/release.json',web/'.next/standalone/public/release.json']:
 p.write_bytes((r/'website-release-before.json').read_bytes());p.chmod(0o644)
PY
echo PAYMENT_MAIN_VERSION_RESTORED_DATABASE_AND_TRANSACTIONS_RETAINED
