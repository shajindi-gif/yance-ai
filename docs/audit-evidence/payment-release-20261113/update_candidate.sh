#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/payment-20261113-01
tar -xzf /home/ubuntu/yance-payment-final-patch.tar.gz -C "$r"
python3 - "$r" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);revision=(r/'SOURCE_REVISION').read_text().strip()
p=r/'Dockerfile.patch';lines=p.read_text().splitlines()
if 'ENV PYTHONPATH=/app' not in lines:
 lines.insert(1,'ENV PYTHONPATH=/app')
if not any('install_dependency.py' in line for line in lines):
 manifest=json.loads((r/'dependency-manifest.json').read_text());wheel=manifest['filename']
 assert wheel=='dnspython-2.9.2-py3-none-any.whl'
 lines[2:2]=['COPY dependency/'+wheel+' /tmp/'+wheel,'COPY dependency-manifest.json /tmp/dependency-manifest.json','COPY install_dependency.py /tmp/install_dependency.py','USER root','RUN apt-get update && apt-get install -y --no-install-recommends zlib1g && rm -rf /var/lib/apt/lists/*','RUN python /tmp/install_dependency.py /tmp/'+wheel+' /tmp/dependency-manifest.json','USER yance']
p.write_text('\n'.join(lines)+'\n')
for name in ['production.env','restore.env','candidate.env']:
 p=r/name;lines=p.read_text().splitlines();p.write_text('\n'.join('APP_SOURCE_REVISION='+revision if x.startswith('APP_SOURCE_REVISION=') else x for x in lines)+'\n')
p=r/'release.override.json';j=json.loads(p.read_text())
for service in j['services'].values():service['environment']['APP_SOURCE_REVISION']=revision
p.write_text(json.dumps(j))
for name in ['website/public/release.json','website/.next/standalone/public/release.json']:
 p=r/name;j=json.loads(p.read_text());j.update(website_source=revision,api_patch_source=revision);p.write_text(json.dumps(j));p.chmod(0o644)
PY
docker build -f "$r/Dockerfile.patch" -t yance-backend:payment-20261113-01 "$r" > "$r/backend-final-build.log" 2>&1
docker rm -f yance-payment-candidate-api > /dev/null
docker run -d --name yance-payment-candidate-api --network yance-prod_default --env-file "$r/candidate.env" -p 127.0.0.1:18013:8000 --entrypoint uvicorn yance-backend:payment-20261113-01 app.main:app --host 0.0.0.0 --port 8000 > "$r/candidate-container.txt"
docker run --rm --network yance-prod_default --env-file "$r/candidate.env" -v "$r/candidate_contract.py:/tmp/candidate_contract.py:ro" --entrypoint python yance-backend:payment-20261113-01 /tmp/candidate_contract.py > "$r/candidate-contract.log" 2>&1
grep -q PG16_SYNTHETIC_TENANT_RETURN_SETTLEMENT_REFUND_REPLAY_PASSED "$r/candidate-contract.log"
# The production-only collection scheduler is intentionally unchanged.
docker exec yance-prod-api-1 sha256sum /app/app/services/policy_collection/scheduler.py | cut -d' ' -f1 > "$r/production-scheduler.sha256"
docker exec yance-payment-candidate-api sha256sum /app/app/services/policy_collection/scheduler.py | cut -d' ' -f1 > "$r/candidate-scheduler.sha256"
cmp "$r/production-scheduler.sha256" "$r/candidate-scheduler.sha256"
if [ -f "$r/REBUILD_WEB" ]; then
 chown -R ubuntu:ubuntu "$r/website"
 sudo -u ubuntu bash -c 'set -e; cd "$1"; npm run lint; npm run typecheck; npm run test:unit; API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r/website" > "$r/frontend-final-build.log" 2>&1
 cp -an "$(cat /opt/yance/backups/payment-20261113-01/website-path.txt)/.next/standalone/.next/static/." "$r/website/.next/standalone/.next/static/"
 chmod 644 "$r/website/public/release.json" "$r/website/.next/standalone/public/release.json"
 systemctl restart yance-payment-candidate-web
fi
echo FINAL_CANDIDATE_PG16_CONTRACT_AND_COLLECTION_PRESERVATION_PASSED
