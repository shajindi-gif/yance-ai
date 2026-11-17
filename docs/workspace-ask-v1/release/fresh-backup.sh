#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/workspace-20261117-01
b=/opt/yance/backups/workspace-20261117-01
test ! -e "$b/database-final.dump"
docker exec yance-prod-db-1 sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$b/database-final.dump"
docker exec yance-prod-db-1 sh -ec 'exec createdb -U "$POSTGRES_USER" yance_workspace_1117_final_restore'
docker exec -i yance-prod-db-1 sh -ec 'exec pg_restore -U "$POSTGRES_USER" -d yance_workspace_1117_final_restore --exit-on-error' < "$b/database-final.dump"
python3 - "$r" <<'PY'
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import sys
r=Path(sys.argv[1]);env=dict(x.split('=',1) for x in (r/'production.env').read_text().splitlines());u=urlsplit(env['DATABASE_URL'])
env['DATABASE_URL']=urlunsplit((u.scheme,u.netloc,'/yance_workspace_1117_final_restore',u.query,u.fragment));env.update(EMAIL_ENABLED='false',SMS_ENABLED='false',POLICY_COLLECTION_ENABLED='false')
(r/'final_restore.env').write_text('\n'.join(k+'='+v for k,v in env.items())+'\n')
PY
for stage in before after; do
 if [ "$stage" = after ]; then docker run --rm --network yance-prod_default --env-file "$r/final_restore.env" --entrypoint alembic yance-backend:workspace-20261117-01 upgrade head > "$r/final-restore-migration.log" 2>&1; fi
 docker run --rm --network yance-prod_default --env-file "$r/final_restore.env" -v "$r/check_database.py:/tmp/check_database.py:ro" --entrypoint python yance-backend:workspace-20261117-01 /tmp/check_database.py > "$r/final-restore-$stage.jsonl"
done
cmp "$r/final-restore-before.jsonl" "$r/final-restore-after.jsonl"
echo FRESH_BACKUP_RESTORED_MIGRATION_PRESERVED_EXISTING_DATA
