#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/sms-20261029-01
b=/opt/yance/backups/sms-20261029-01
old=/opt/yance/releases/growth-20261029-01
web=/opt/yance/releases/website-images-20261029-01/website
sha=$1; commit=$2
[[ "$commit" =~ ^[a-f0-9]{40}$ ]]
test "$(sha256sum /home/ubuntu/yance-sms-20261029.tar.gz | cut -d' ' -f1)" = "$sha"
test ! -e "$r"
test "$(systemctl show yance-website -p WorkingDirectory --value)" = "$web"
test "$(docker exec yance-prod-db-1 psql -U yance -d yance_prod -Atqc 'select version_num from alembic_version;')" = 20261027_0033
install -d -o ubuntu -g ubuntu -m 755 "$r"
tar -xzf /home/ubuntu/yance-sms-20261029.tar.gz -C "$r"
cp -a "$r/docs/audit-evidence/sms-release-20261029" "$r/ops"
mkdir -p "$b"; chmod 700 "$b"
printf '%s\n' "$commit" > "$r/source-commit.txt"
cp -a "$old/yance-ai/.env.prod" "$r/yance-ai/.env.prod"
cp -a "$old/yance-ai/.env.prod" "$b/backend-env.private"
cp -a "$old/yance-ai/release.override.yml" "$b/backend-override.yml"
cp -a /etc/systemd/system/yance-website.service.d "$b/service-before"
cp -a "$web/.env.local" "$r/website/.env.local"
python3 - "$r" "$commit" <<'PY'
from pathlib import Path
import re,sys
r=Path(sys.argv[1]);commit=sys.argv[2]
p=r/'yance-ai/.env.prod';s=p.read_text()
assert len(re.findall(r'^APP_VERSION=',s,re.M))==1
s=re.sub(r'^APP_VERSION=.*$', 'APP_VERSION='+commit,s,flags=re.M)
sms=Path('/home/ubuntu/.config/yance/tencent-sms.pending.env').read_text()
keys=[line.split('=',1)[0] for line in sms.splitlines() if '=' in line]
s='\n'.join(line for line in s.splitlines() if line.split('=',1)[0] not in keys)+'\n'+sms+'SMS_DAILY_LIMIT=100\n'
p.write_text(s);p.chmod(0o600)
s=Path('/opt/yance/releases/growth-20261029-01/yance-ai/release.override.yml').read_text().replace('4587e34251a1ebcd85c55ae706f1a82ceb25de2b',commit).replace('growth-20261029-01','sms-20261029-01')
(r/'yance-ai/release.override.yml').write_text(s)
PY
docker build --memory 1g -t yance-backend:sms-20261029-01 "$r/yance-ai" > "$r/backend-build.log" 2>&1
chown -R ubuntu:ubuntu "$r/website"
sudo -u ubuntu bash -c 'set -e; cd "$1/website"; npm ci; npm run typecheck; npm run test:unit; npm audit --omit=dev --audit-level=high; NODE_OPTIONS=--max-old-space-size=768 API_PROXY_TARGET=http://127.0.0.1:8000 NEXT_PUBLIC_API_URL=/api/v1 NEXT_TELEMETRY_DISABLED=1 npm run build' _ "$r" > "$r/website-build.log" 2>&1
python3 "$r/ops/recovery.py" backup "$b/sms-preflight" > "$r/preflight-backup.json"
docker run --rm --network container:yance-recovery-sms-preflight -e APP_ENV=test -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_release_test yance-backend:sms-20261029-01 alembic upgrade head > "$r/clone-migration.log" 2>&1
python3 "$r/ops/recovery.py" verify "$b/sms-preflight" yance-recovery-sms-preflight yance_release_test > "$r/clone-preservation.json"
# Both old and new ORM can read original users on migrated clone, no data output.
docker run --rm --network container:yance-recovery-sms-preflight -e APP_ENV=test -e DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:5432/yance_release_test yance-backend:growth-20261029-01 python -c 'from app.core.db import SessionLocal; from app.models.models import User; from sqlalchemy import select; from app.schemas.schemas import UserOut; d=SessionLocal(); [UserOut.model_validate(u) for u in d.scalars(select(User)).all()]; print("OLD_USER_CONTRACT_READ_PASSED")' > "$r/old-contract-check.txt"
docker stop yance-recovery-sms-preflight >/dev/null
tar --exclude='./.next/cache' -czf "$b/website-before.tar.gz" -C "$web" .
mkdir "$b/website-restore";tar -xzf "$b/website-before.tar.gz" -C "$b/website-restore"
python3 - "$web" "$b/website-restore" <<'PY'
from pathlib import Path
import hashlib,sys
def hashes(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink() and not str(p.relative_to(root)).startswith('.next/cache/')}
assert hashes(sys.argv[1])==hashes(sys.argv[2])
print('WEBSITE_RESTORE_MATCHED')
PY
printf 'PREPARED_NOT_ACTIVATED\n'
