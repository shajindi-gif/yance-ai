import json,re,subprocess as sp
from pathlib import Path
ns={'sp':sp,'re':re}
s=Path('/tmp/yance-backup-restore-verify.py').read_text()
exec(s[s.index('def run('):s.index('keeper =')],ns)
r=json.loads(Path('/opt/yance-backups/release-7f466d0-final/verification.json').read_text())
after=ns['hashes']('yance-prod-db-1','yance_prod',compatible=True)
before=r['compatibility_hashes']
changes=[name for name in before if name!='alembic_version' and before[name]!=after.get(name)]
version=ns['psql']('yance-prod-db-1','yance_prod','SELECT version_num FROM alembic_version;').strip()
assert version=='20261020_0027' and not changes, 'unexpected production data change'
report={'revision':version,'existing_business_tables_verified':len(before)-1,'changed_tables':changes,'verified':True}
Path('/opt/yance/releases/backend-7f466d0/production-migration-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
