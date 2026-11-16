"""Bind scanner config/layers to Docker's image index and fixed source files."""
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

r = Path("/opt/yance/releases/payment-20261113-01")
assert (r / "SOURCE_REVISION").read_text().strip() == "4332071c804fc6e3f045746a5b71354e49ad4e57"
log = Path("/home/ubuntu/yance-payment-final-verify.log").read_text()
assert "FINAL_CANDIDATE_PG16_CONTRACT_AND_COLLECTION_PRESERVATION_PASSED" in log
assert "ACTUAL_CANDIDATE_IMAGE_FIXED_HIGH_CRITICAL_GATE_PASSED" in log
scan = json.loads((r / "actual-image-scan.json").read_text())
assert not [v for item in scan.get("Results", []) for v in item.get("Vulnerabilities") or []]
image = json.loads(subprocess.check_output(["docker", "image", "inspect", "yance-backend:payment-20261113-01"]))[0]
container = json.loads(subprocess.check_output(["docker", "inspect", "yance-payment-candidate-api"]))[0]
assert container["Image"] == image["Id"]
assert image["Config"]["User"] not in ["root", "0", ""]
assert image["RootFS"]["Layers"] == scan["Metadata"]["DiffIDs"]
# Docker uses an OCI index ID here; Trivy records the config ID. Verify their
# relationship from the exported archive instead of treating the IDs as equal.
archive = r / "identity-image.tar"
subprocess.run(["docker", "image", "save", "yance-backend:payment-20261113-01", "-o", str(archive)], check=True)
with tarfile.open(archive) as tar:
    manifests = json.load(tar.extractfile("manifest.json"))
    assert len(manifests) == 1
    config = tar.extractfile(manifests[0]["Config"]).read()
    assert "sha256:" + hashlib.sha256(config).hexdigest() == scan["Metadata"]["ImageID"]
    assert json.loads(config)["rootfs"]["diff_ids"] == image["RootFS"]["Layers"]
assert subprocess.check_output(["docker", "image", "inspect", "-f", "{{.Id}}", "yance-backend:payment-20261113-01"], text=True).strip() == image["Id"]
archive.unlink()
expected = json.loads(Path("/home/ubuntu/yance-payment-patch-hashes.json").read_text())
script = (
    "from pathlib import Path\nimport hashlib,json\nexpected=json.loads(" + repr(json.dumps(expected)) + ")\n"
    "for name,sha in expected.items():\n assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==sha,name\n"
    "print('MATCHED_FIXED_SOURCE_FILES',len(expected))\n"
)
result = subprocess.run(["docker", "exec", "-i", "yance-payment-candidate-api", "python", "-"], input=script, text=True, capture_output=True, check=True)
(r / "source-hash-check.log").write_text(result.stdout)
(r / "approved-image-id.txt").write_text(image["Id"] + "\n")
(r / "approved.txt").write_text("CANDIDATE_PG16_CONTRACTS_AND_WEB_PASSED\nCI 43589593659 success; source4332071; actual image fixed high/critical zero; candidate browser passed\n")
(r / "image-identity.json").write_text(json.dumps({"docker_index_id": image["Id"], "scanned_config_id": scan["Metadata"]["ImageID"], "layers_matched": len(image["RootFS"]["Layers"]), "source_files_matched": len(expected)}, indent=2) + "\n")
print(result.stdout.strip())
print("FIXED_IMAGE_CONFIG_LAYERS_AND_SOURCE_APPROVED")
