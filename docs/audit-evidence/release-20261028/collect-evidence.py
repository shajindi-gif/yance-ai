"""Export only allowlisted aggregate reports. Never read private backup data."""
import json
from pathlib import Path
import subprocess as sp

root=Path('/opt/yance/releases/full-20261028-01')
reports={}
for name in ['recovery-preflight.json','rehearsal-preservation.json',
             'legacy-baseline-drift.json','legacy-migrated-drift.json',
             'candidate-readonly-checks.log','worker-shutdown.json',
             'recovery-final-retry.json','final-retry-clone-preservation.json',
             'final-retry-candidate-checks.log','production-preservation.json']:
    reports[name]=json.loads((root/name).read_text().splitlines()[-1])
seal=Path('/opt/yance/backups/full-20261028-01/final/sealing-verification.json')
reports['failed-snapshot-sealing']=json.loads(seal.read_text())


def output(args):
    return sp.run(args,check=True,text=True,capture_output=True).stdout.strip()


operational={
    'public_health':json.loads(output(['curl','--max-time','15','-fsS','https://api.yance.ai/health'])),
    'website_service':output(['systemctl','show','yance-website','-p','ActiveState','-p','WorkingDirectory']),
    'running_containers':output(['docker','ps','--format','{{.Names}} {{.Image}} {{.Status}}']),
    'database_revision':output(['docker','exec','yance-prod-db-1','psql','-U','yance','-d','yance_prod','-Atqc','SELECT version_num FROM alembic_version;']),
    'observed_at_utc':output(['date','-u','+%FT%TZ']),
}
logs=sp.run(['docker','logs','--tail','2000','yance-prod-api-1'],check=True,capture_output=True,text=True)
statuses={}; errors=0; parsed=0; line_count=0
for line in (logs.stdout+'\n'+logs.stderr).splitlines():
    line_count+=1
    try:
        value=json.loads(line)
    except (ValueError,TypeError):
        continue
    if not isinstance(value,dict):
        continue
    parsed+=1
    code=value.get('status_code')
    if isinstance(code,int):
        statuses[str(code)]=statuses.get(str(code),0)+1
    if value.get('level') in {'error','critical'}:
        errors+=1
operational['api_log_observation']={'scope':'newly_created_api_container_last_2000_lines','lines':line_count,'parsed_json_records':parsed,'status_counts':statuses,'error_level_events':errors if parsed else None,'private_log_contents_exported':False,'continuous_monitoring':False}
print(json.dumps({'source':(root/'source-commit.txt').read_text().strip(),'source_archive_sha256':(root/'source-archive-sha256.txt').read_text().strip(),'image_id':(root/'backend-image-id.txt').read_text().strip(),'reports':reports,'operational':operational},indent=2))
