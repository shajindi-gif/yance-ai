#!/usr/bin/env sh
set -eu

BASE_URL="${1:-http://localhost}"
echo "Checking ${BASE_URL}/health"
curl --fail --silent --show-error "${BASE_URL}/health"
echo
echo "Checking ${BASE_URL}/health/ready"
curl --fail --silent --show-error "${BASE_URL}/health/ready"
echo
echo "Smoke test passed"

