"""Install the one verified pure-Python wheel inside the new image, never the host."""
import hashlib
import importlib.metadata
import json
import shutil
import site
import sys
import zipfile
from pathlib import Path, PurePosixPath

wheel, manifest = map(Path, sys.argv[1:])
expected = json.loads(manifest.read_text())
assert expected["name"] == "dnspython" and expected["version"] == "2.9.2"
assert wheel.name == expected["filename"]
assert hashlib.sha256(wheel.read_bytes()).hexdigest() == expected["sha256"]
target = Path(site.getsitepackages()[0])
assert target == Path("/opt/venv/lib/python3.12/site-packages")
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        path = PurePosixPath(name)
        assert not path.is_absolute() and ".." not in path.parts
        assert path.parts[0] in {"dns", "dnspython-2.9.2.dist-info"}
    # This is an immutable candidate image layer, not a running container or DB.
    shutil.rmtree(target / "dns")
    for old in target.glob("dnspython-*.dist-info"):
        shutil.rmtree(old)
    archive.extractall(target)
assert importlib.metadata.version("dnspython") == "2.9.2"
print("PATCHED_DNS_DEPENDENCY_INSTALLED_FROM_VERIFIED_WHEEL")
