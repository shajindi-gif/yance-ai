#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/payment-metrics-20261115-02
test ! -e "$r"
install -d -m 700 "$r"
tar -xzf /home/ubuntu/yance-metrics-patch.tar.gz -C "$r"
python3 - "$r" <<'PY'
import json,subprocess,sys
from pathlib import Path
r=Path(sys.argv[1]);services={};rollback={}
for service in ['api','agent-worker','payment-expiry','payment-reconcile']:
 c=json.loads(subprocess.check_output(['docker','inspect','yance-prod-'+service+'-1']))[0]
 env=dict(x.split('=',1) for x in c['Config']['Env'])
 rollback[service]={'image':c['Image'],'environment':env.copy()}
 env.update(APP_VERSION='payment-metrics-20261115-02',APP_SOURCE_REVISION=(r/'SOURCE_REVISION').read_text().strip())
 services[service]={'image':'yance-backend:payment-metrics-20261115-02','environment':env}
(r/'rollback.override.json').write_text(json.dumps({'services':rollback}))
(r/'release.override.json').write_text(json.dumps({'services':services}))
subprocess.run(['docker','tag',rollback['api']['image'],'yance-backend:payment-metrics-base'],check=True)
(r/'Dockerfile').write_text('FROM yance-backend:payment-metrics-base\nCOPY --chown=yance:yance metrics.py /app/app/services/admin/metrics.py\n')
web=Path('/opt/yance/website').resolve()
(r/'website-path.txt').write_text(str(web))
(r/'website-release-before.json').write_bytes((web/'public/release.json').read_bytes())
PY
docker build -t yance-backend:payment-metrics-20261115-02 "$r" > "$r/build.log" 2>&1
# A restored production snapshot is queried read-only; never mark demo rows paid
# or rewrite their provenance to make a metric look better.
docker run --rm -i --network yance-prod_default --env-file /opt/yance/releases/payment-20261113-01/preswitch_restore.env --entrypoint python yance-backend:payment-metrics-20261115-02 - <<'PY' > "$r/metrics-check.log"
import json
from sqlalchemy import select,text,func
from app.core.db import SessionLocal
from app.models.models import Order,Payment
from app.services.admin.metrics import investor_metrics
with SessionLocal() as db:
 db.execute(text('SET TRANSACTION READ ONLY'))
 before=[db.scalar(select(func.count()).select_from(m)) for m in [Order,Payment]]
 result=investor_metrics(db)
 assert result['totals']['paying_customers']==0
 assert result['revenue_by_currency']==[]
 assert result['totals']['unverified_paid_orders']==23
 after=[db.scalar(select(func.count()).select_from(m)) for m in [Order,Payment]]
 assert before==after
 print(json.dumps({'restored_snapshot_counts':before,'paying_customers':0,'recognized_revenue':[],'unverified_paid_orders':23,'read_only':True}))
PY
docker save yance-backend:payment-metrics-20261115-02 -o "$r/image.tar"
docker run --rm -v "$r/image.tar:/scan/image.tar:ro" -v /opt/yance/releases/payment-20261113-01/trivy-cache:/root/.cache/trivy aquasec/trivy:0.70.0 image --input /scan/image.tar --timeout 10m --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --format json > "$r/scan.json" 2> "$r/scan.stderr"
python3 - "$r" <<'PY'
import json,hashlib,subprocess,sys,tarfile
from pathlib import Path
r=Path(sys.argv[1]);s=json.loads((r/'scan.json').read_text());i=json.loads(subprocess.check_output(['docker','image','inspect','yance-backend:payment-metrics-20261115-02']))[0]
assert not [v for x in s.get('Results',[]) for v in x.get('Vulnerabilities') or []]
assert s['Metadata']['DiffIDs']==i['RootFS']['Layers']
with tarfile.open(r/'image.tar') as t:
 m=json.load(t.extractfile('manifest.json'));assert len(m)==1
 assert 'sha256:'+hashlib.sha256(t.extractfile(m[0]['Config']).read()).hexdigest()==s['Metadata']['ImageID']
(r/'approved-image-id.txt').write_text(i['Id'])
(r/'image-summary.json').write_text(json.dumps({'image':i['Id'],'config':s['Metadata']['ImageID'],'fixed_high_critical':0,'layers':len(i['RootFS']['Layers'])},indent=2))
PY
rm "$r/image.tar"
echo METRICS_RESTORED_SNAPSHOT_READ_ONLY_AND_ACTUAL_IMAGE_PASSED
