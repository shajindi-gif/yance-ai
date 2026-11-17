"""Copy only absent content-addressed assets, rejecting conflicting content."""
import hashlib
import shutil
import sys
from pathlib import Path
source, destination = map(Path, sys.argv[1:])
for item in source.rglob('*'):
    target = destination / item.relative_to(source)
    if item.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        target.chmod(0o755)
    elif item.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.parent.chmod(0o755)
        if target.exists():
            assert hashlib.sha256(item.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest(), 'Static asset conflict'
        else:
            shutil.copy2(item, target)
