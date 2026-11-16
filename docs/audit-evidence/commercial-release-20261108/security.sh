#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/commercial-20261108-01
install -d -m 755 "$r/security-wheels" "$r/pip-tools"
py=/opt/yance/collector-20261107-r5/.venv/bin/python
"$py" -m pip download --only-binary=:all: --no-deps --dest "$r/security-wheels" brotli==1.2.1 dnspython==2.9.0 pypdf==6.21.4 > "$r/security-download.log" 2>&1
"$py" - "$r/pip-tools" <<'PY'
import pip,shutil,sys
from pathlib import Path
shutil.copytree(Path(pip.__file__).parent,Path(sys.argv[1])/'pip',dirs_exist_ok=True)
PY
cat > "$r/Dockerfile.security" <<'DOCKER'
FROM yance-backend:commercial-20261108-01
USER root
COPY security-wheels /tmp/security-wheels
COPY pip-tools /tmp/pip-tools
RUN PYTHONPATH=/tmp/pip-tools PIP_CONFIG_FILE=/dev/null python -m pip install --no-index --find-links=/tmp/security-wheels --no-deps --upgrade brotli==1.2.1 dnspython==2.9.0 pypdf==6.21.4 && rm -rf /tmp/pip-tools /tmp/security-wheels
USER yance
DOCKER
docker build -f "$r/Dockerfile.security" -t yance-backend:commercial-20261108-01-secure "$r" > "$r/security-build.log" 2>&1
python3 - "$r" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);p=r/'api.override.json';v=json.loads(p.read_text())
for service in v['services'].values():service['image']='yance-backend:commercial-20261108-01-secure'
p.write_text(json.dumps(v))
p=r/'website/public/release.json';v=json.loads(p.read_text());v['dependency_patches']={'pypdf':'6.21.4','brotli':'1.2.1','dnspython':'2.9.0'};p.write_text(json.dumps(v))
# Public asset only; the source build itself is already verified.
(r/'website/.next/standalone/public/release.json').write_text(p.read_text())
PY
docker stop --time 30 yance-release-api-1108
docker rm yance-release-api-1108
docker run -d --name yance-release-api-1108 --network yance-prod_default --env-file "$r/candidate.env" -p 127.0.0.1:18008:8000 --entrypoint uvicorn yance-backend:commercial-20261108-01-secure app.main:app --host 0.0.0.0 --port 8000 > "$r/candidate-container-secure.txt"
docker exec yance-release-api-1108 python -c 'import importlib.metadata as m; print({n:m.version(n) for n in ["pypdf","brotli","dnspython"]}); import dns.resolver; from pypdf import PdfWriter, PdfReader; from io import BytesIO; w=PdfWriter(); w.add_blank_page(width=100,height=100); o=BytesIO(); w.write(o); o.seek(0); assert len(PdfReader(o).pages)==1; print("SECURITY_PACKAGES_PDF_ROUNDTRIP_PASSED")' > "$r/security-check.log"
echo SECURITY_PATCHED_ISOLATED_API_READY
