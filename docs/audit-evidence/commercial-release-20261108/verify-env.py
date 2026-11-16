import json,subprocess
from pathlib import Path
r=Path('/opt/yance/releases/commercial-20261108-01');b=Path('/opt/yance/backups/commercial-20261108-01')
old=json.loads((b/'rollback-api.json').read_text())['services']
for service,container in [('api','yance-prod-api-1'),('agent-worker','yance-prod-agent-worker-1')]:
 c=json.loads(subprocess.check_output(['docker','inspect',container]))[0]
 live=dict(v.split('=',1) for v in c['Config']['Env'])
 expected=old[service]['environment'].copy();expected.update(APP_VERSION='web-20261106-05+68b3d5b',APP_SOURCE_REVISION='68b3d5b')
 if service=='agent-worker':expected['EMAIL_ENABLED']='false'
 assert live==expected, service+' runtime environment differs from approved configuration'
 print(service.upper()+'_RUNTIME_CONFIG_PRESERVED')
