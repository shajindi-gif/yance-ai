#!/usr/bin/env bash
set -euo pipefail
umask 077
backup=/opt/yance/backups/website-images-20261029-01
old=/opt/yance/releases/growth-20261029-01/website
restore=/opt/yance/releases/website-restore-images-20261029-01
[ "$(systemctl show yance-website -p WorkingDirectory --value)" = "$old" ]
[ ! -e "$backup" ] && [ ! -e "$restore" ]
mkdir -p "$backup" "$restore"
chmod 700 "$backup"
systemctl cat yance-website > "$backup/service-before.conf"
cp -a /etc/systemd/system/yance-website.service "$backup/"
cp -a /etc/systemd/system/yance-website.service.d "$backup/"
readlink -f /opt/yance/website > "$backup/website-link-before.txt"
tar --exclude='./.next/cache' -czf "$backup/website-before.tar.gz" -C "$old" .
sha256sum "$backup/website-before.tar.gz" > "$backup/website-before.sha256"
tar -xzf "$backup/website-before.tar.gz" -C "$restore"
python3 - "$old" "$restore" <<'PY'
from pathlib import Path
import hashlib,json,sys

def hashes(base):
 out={}
 for p in Path(base).rglob('*'):
  rel=p.relative_to(base).as_posix()
  if rel.startswith('.next/cache/') or p.is_symlink() or not p.is_file():continue
  out[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 return out
before=hashes(sys.argv[1]);after=hashes(sys.argv[2])
if before!=after:raise SystemExit('Backup restore byte comparison failed')
print(json.dumps({'backup_restored':True,'regular_files':len(before),'excluded':'.next/cache; symlink targets not hashed'}))
PY
chown -R ubuntu:ubuntu "$restore"
sha256sum "$backup/website-before.tar.gz"
printf 'backup=%s\nrestore=%s\n' "$backup" "$restore"
