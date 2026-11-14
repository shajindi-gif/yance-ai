#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/web-20261031-01
[ -f "$r/website/.next/standalone/server.js" ]
if ! docker exec yance-prod-db-1 psql -U yance -d postgres -Atqc "select datname from pg_database where datname='yance_web_auth_test'" | grep -qx yance_web_auth_test; then
 docker exec yance-prod-db-1 createdb -U yance yance_web_auth_test
fi
python3 - "$r" <<'PY'
import json,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
env=json.loads(subprocess.check_output(['docker','inspect','yance-prod-api-1']))[0]['Config']['Env']
d=dict(x.split('=',1) for x in env if '=' in x)
u=urlsplit(d['DATABASE_URL']);d['DATABASE_URL']=urlunsplit((u.scheme,u.netloc,'/yance_web_auth_test','',''))
d.update(APP_ENV='test',EMAIL_ENABLED='false',SMS_ENABLED='false',LLM_DEFAULT_PROVIDER='mock')
for k in list(d):
 if any(s in k for s in ['SECRET','API_KEY','ACCESS_KEY','SMTP_PASSWORD']):d[k]=''
d.update(JWT_SECRET='isolated-contract-secret-at-least-32-characters', API_KEY_PEPPER='isolated-contract-pepper-at-least-32-characters')
p=Path(sys.argv[1])/'test.private.env';p.write_text(''.join(k+'='+v+'\n' for k,v in d.items()));p.chmod(0o600)
PY
docker run --rm --network yance-prod_default --env-file "$r/test.private.env" yance-backend:web-auth-20261031-01 alembic upgrade head > "$r/test-migration.log" 2>&1
docker run --rm --network yance-prod_default --env-file "$r/test.private.env" -v "$r/auth-contract.py:/app/auth-contract.py:ro" yance-backend:web-auth-20261031-01 python /app/auth-contract.py > "$r/auth-contract.log" 2>&1
rm "$r/test.private.env"
systemd-run --unit=yance-web-candidate-1031 --property=WorkingDirectory="$r/website" --setenv=NODE_ENV=production --setenv=HOSTNAME=127.0.0.1 --setenv=PORT=3042 /usr/bin/node "$r/website/.next/standalone/server.js"
sleep 2
python3 - <<'PY'
import json,urllib.request
for path in ['/','/login','/pricing','/checkout','/success','/release.json','/api/v1/auth/config']:
 with urllib.request.urlopen('http://127.0.0.1:3042'+path,timeout=20) as r: assert r.status==200
 print(path,'OK')
print('CANDIDATE_GET_CHECKS_PASSED')
PY
