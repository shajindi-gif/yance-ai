#!/usr/bin/env bash
# Audit the actual patched image, in addition to CI's fresh source build.
set -Eeuo pipefail
umask 077
r=/opt/yance/releases/payment-20261113-01
install -d -m 700 "$r/trivy-cache"
docker save yance-backend:payment-20261113-01 -o "$r/candidate-image.tar"
# A read-only archive avoids granting the scanner access to the Docker socket.
docker run --rm -v "$r/candidate-image.tar:/scan/candidate-image.tar:ro" -v "$r/trivy-cache:/root/.cache/trivy" \
 aquasec/trivy:0.70.0 image --input /scan/candidate-image.tar --timeout 10m \
 --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
 --format json > "$r/actual-image-scan.json" 2> "$r/actual-image-scan.stderr"
rm "$r/candidate-image.tar"
echo ACTUAL_CANDIDATE_IMAGE_FIXED_HIGH_CRITICAL_GATE_PASSED
