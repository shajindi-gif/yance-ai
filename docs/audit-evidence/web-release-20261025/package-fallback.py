"""Package a tracked old UI with pinned security dependencies from a tracked new commit."""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[3]
ui_commit = "ab504587ec0a64b75f5d259084e587ec97c29c9f"
dependency_commit = subprocess.check_output(
    ["git", "rev-parse", "--verify", sys.argv[1] + "^{commit}"], cwd=root, text=True
).strip()
output = Path(sys.argv[2]).resolve()
if not output.is_relative_to(Path("/private/tmp")):
    raise RuntimeError("Only an isolated local package destination is allowed")
with tempfile.TemporaryDirectory(prefix="yance-fallback-source-") as folder:
    temporary = Path(folder)
    archive = subprocess.check_output(["git", "archive", ui_commit, "website"], cwd=root)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(temporary, filter="data")
    for name in ["package.json", "package-lock.json"]:
        content = subprocess.check_output(
            ["git", "show", f"{dependency_commit}:website/{name}"], cwd=root
        )
        (temporary / "website" / name).write_bytes(content)
    assert json.loads((temporary / "website/package.json").read_text())["dependencies"]["next"] == "16.4.3"
    manifest = {"ui_commit": ui_commit, "dependency_commit": dependency_commit, "next": "16.4.3"}
    (temporary / "fallback-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with tarfile.open(output, "w:gz") as target:
        target.add(temporary / "website", arcname="website")
        target.add(temporary / "fallback-manifest.json", arcname="fallback-manifest.json")
print(json.dumps({**manifest, "archive_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
