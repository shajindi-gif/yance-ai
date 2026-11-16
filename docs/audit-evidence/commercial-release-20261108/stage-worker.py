import json,subprocess
from pathlib import Path
r=Path('/opt/yance/releases/commercial-20261108-01');b=Path('/opt/yance/backups/commercial-20261108-01')
c=json.loads(subprocess.check_output(['docker','inspect','yance-prod-agent-worker-1']))[0]
env=dict(item.split('=',1) for item in c['Config']['Env'])
old=json.loads((b/'rollback-api.json').read_text());old['services']['agent-worker']={'image':c['Image'],'environment':env};(b/'rollback-api.json').write_text(json.dumps(old))
new=json.loads((r/'api.override.json').read_text());env.update(APP_VERSION='web-20261106-05+68b3d5b',APP_SOURCE_REVISION='68b3d5b',EMAIL_ENABLED='false');new['services']['agent-worker']={'image':'yance-backend:commercial-20261108-01','environment':env};(r/'api.override.json').write_text(json.dumps(new))
print('WORKER_CONFIG_SNAPSHOTTED_OUTBOUND_EMAIL_DISABLED')
