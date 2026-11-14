import json,hashlib,subprocess as sp
from pathlib import Path
r=Path('/opt/yance/releases/growth-20261029-01')
b=Path('/opt/yance/backups/growth-20261029-01')
def run(args):return sp.run(args,check=True,capture_output=True,text=True).stdout.strip()
health=json.loads(run(['curl','--max-time','15','-fsS','https://api.yance.ai/health']))
assert health['version']=='4587e34251a1ebcd85c55ae706f1a82ceb25de2b'
config=json.loads(run(['curl','--max-time','15','-fsS','http://127.0.0.1:8000/api/v1/auth/config']))
assert config['checkout_idempotency_revision']==1
backup=json.loads((r/'backup-verification.json').read_text());assert backup['verified']
assert 'WEBSITE_BACKUP_RESTORE_MATCHED' in Path('/home/ubuntu/yance-growth-deploy.log').read_text()
print(json.dumps({'health':health,'checkout_idempotency_revision':config['checkout_idempotency_revision'],'backup':backup,'website_backup_sha256':hashlib.file_digest((b/'website-before.tar.gz').open('rb'),'sha256').hexdigest(),'website_restore_hash_verified':True,'website':run(['systemctl','show','yance-website','-p','WorkingDirectory','-p','ActiveState']),'containers':run(['docker','ps','--format','{{.Names}} {{.Image}} {{.Status}}']),'image_id':run(['docker','image','inspect','yance-backend:growth-20261029-01','--format','{{.Id}}']),'database_revision':run(['docker','exec','yance-prod-db-1','psql','-U','yance','-d','yance_prod','-Atqc','select version_num from alembic_version;']),'at_utc':run(['date','-u','+%FT%TZ']),'production_business_tests':False},indent=2))
