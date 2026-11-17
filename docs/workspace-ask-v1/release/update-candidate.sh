#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/workspace-20261117-01
# Full revision supplied from the fixed local commit, never an arbitrary branch pull.
revision=$(cat /home/ubuntu/yance-workspace-fixed-revision.txt)
cp /home/ubuntu/yance-workspace-AnswerWithCitations.tsx "$r/website/components/workspace/AnswerWithCitations.tsx"
cp /home/ubuntu/yance-workspace-parks-page.tsx "$r/website/app/parks/page.tsx"
cp /home/ubuntu/yance-workspace-parks-page.module.css "$r/website/app/parks/page.module.css"
chown ubuntu:ubuntu "$r/website/app/parks/page.tsx" "$r/website/app/parks/page.module.css"
chmod 644 "$r/website/app/parks/page.tsx" "$r/website/app/parks/page.module.css"
chown ubuntu:ubuntu "$r/website/components/workspace/AnswerWithCitations.tsx"
chmod 644 "$r/website/components/workspace/AnswerWithCitations.tsx"
python3 - "$r" "$revision" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);rev=sys.argv[2];assert len(rev)==40
(r/'SOURCE_REVISION').write_text(rev)
p=r/'release.override.json';x=json.loads(p.read_text())
for service in x['services'].values():service['environment']['APP_SOURCE_REVISION']=rev
p.write_text(json.dumps(x))
for name in ['production.env','restore.env']:
 p=r/name;env=dict(line.split('=',1) for line in p.read_text().splitlines());env['APP_SOURCE_REVISION']=rev;p.write_text('\n'.join(k+'='+v for k,v in env.items())+'\n')
p=r/'website/public/release.json';x=json.loads(p.read_text());x.update(website_source=rev,api_source=rev);p.write_text(json.dumps(x));p.chmod(0o644)
PY
systemctl stop yance-workspace-candidate-web
sudo -u ubuntu bash -c 'set -e; cd "$1"; npm run lint; npm run typecheck; npm run test:unit; API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r/website" > "$r/frontend-build-final.log" 2>&1
python3 "$r/copy_static.py" "$(cat /opt/yance/backups/workspace-20261117-01/website-path.txt)/.next/standalone/.next/static" "$r/website/.next/standalone/.next/static"
docker rm -f yance-workspace-candidate-api > /dev/null
docker run -d --name yance-workspace-candidate-api --network yance-prod_default --env-file "$r/restore.env" -p 127.0.0.1:8037:8000 yance-backend:workspace-20261117-01 > "$r/candidate-id-final.txt"
systemctl start yance-workspace-candidate-web
echo FIXED_CANDIDATE_REBUILT_PRODUCTION_UNCHANGED
