#!/usr/bin/env bash
# Install the pinned collector release on the server.  Does NOT start anything.
#
# What it does, in order:
#   1. verifies the release manifest against SHA256SUMS (refuses a tampered tarball),
#   2. unpacks into /opt/yance/collector-<REV> (never into the production app dir),
#   3. derives .env.collector from the existing .env.prod — only the variables the
#      crawler actually needs, so payment / SMS / JWT secrets never enter this container,
#   4. builds the collector image FROM the already-deployed backend image (offline),
#   5. smokes it: imports the worker, prints the alembic head the release expects.
#
# It does NOT: start the collector, run migrations, restart the api, or touch the db.
#
# Usage (as root, from the unpacked release directory):
#   sudo ./ops/collector-install.sh
#   sudo ./ops/collector-install.sh --base-image yance-backend:web-auth-20261031-01

set -euo pipefail

RELEASE="20261106-r2"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/yance}"
TARGET_DIR="${INSTALL_ROOT}/collector-${RELEASE}"
PROD_ENV="${PROD_ENV:-/opt/yance/yance-ai/.env.prod}"
BASE_IMAGE="${BASE_IMAGE:-yance-backend:web-auth-20261031-01}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-image) BASE_IMAGE="$2"; shift 2 ;;
    --install-root) INSTALL_ROOT="$2"; TARGET_DIR="${INSTALL_ROOT}/collector-${RELEASE}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

die() { echo "error: $*" >&2; exit 1; }
log() { echo "== $*"; }

[[ "$(id -u)" -eq 0 ]] || die "run as root (sudo)"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---- 1. manifest -------------------------------------------------------------
[[ -f "${SRC_DIR}/SHA256SUMS" ]] || die "SHA256SUMS missing next to the release"
log "verifying release manifest"
( cd "${SRC_DIR}" && sha256sum -c SHA256SUMS --quiet ) || die "manifest verification failed"

# ---- 2. unpack ---------------------------------------------------------------
if [[ "${SRC_DIR}" != "${TARGET_DIR}" ]]; then
  log "installing to ${TARGET_DIR}"
  mkdir -p "${TARGET_DIR}"
  # rsync keeps the previous install recoverable if this one is interrupted.
  tar -C "${SRC_DIR}" -cf - . | tar -C "${TARGET_DIR}" -xf -
else
  log "already installed at ${TARGET_DIR}"
fi

# macOS tar writes AppleDouble `._*` sidecars.  They are binary, they end in .py for
# python files, and alembic imports every *.py it finds — so one of them turns
# `alembic heads` into "source code string cannot contain null bytes".  Strip them.
find "${TARGET_DIR}" -name '._*' -delete
find "${TARGET_DIR}" -name '.DS_Store' -delete

# ---- 3. env for the collector only ------------------------------------------
log "generating ${TARGET_DIR}/.env.collector from ${PROD_ENV}"
[[ -r "${PROD_ENV}" ]] || die "cannot read ${PROD_ENV}"

# Whitelist: the crawler needs the database URL and nothing else from production
# secrets.  Everything that talks to money, SMS, WeChat or auth stays out.
WHITELIST="DATABASE_URL APP_ENV POLICY_ENGINE_V2 CLAMD_HOST MALWARE_SCAN_MODE DOCUMENT_OCR_ENABLED"
TMP_ENV="$(mktemp)"
trap 'rm -f "${TMP_ENV}"' EXIT
: > "${TMP_ENV}"
for key in ${WHITELIST}; do
  line="$(grep -m1 "^${key}=" "${PROD_ENV}" || true)"
  [[ -n "${line}" ]] && printf '%s\n' "${line}" >> "${TMP_ENV}"
done
grep -q '^DATABASE_URL=' "${TMP_ENV}" || die "DATABASE_URL not found in ${PROD_ENV}"

cat >> "${TMP_ENV}" <<'EOF'
# ---- collector runtime (values mirror docker-compose.collector.yml) ----
POLICY_COLLECTION_ENABLED=true
POLICY_COLLECTION_RAW_DIR=/app/policy_raw
POLICY_COLLECTION_ATTACHMENT_DIR=/app/policy_raw/attachments
POLICY_COLLECTION_MIN_FREE_DISK_MB=3000
POLICY_COLLECTION_SCHEDULER_CYCLE_SECONDS=600
POLICY_COLLECTION_SCHEDULER_INTERVAL_SECONDS=300
POLICY_COLLECTION_DNS_PROXY_CIDRS=
EOF
install -m 0640 -o root -g "$(id -gn ubuntu 2>/dev/null || echo root)" "${TMP_ENV}" "${TARGET_DIR}/.env.collector"
log "wrote ${TARGET_DIR}/.env.collector (variables: $(grep -c '^[A-Z]' "${TARGET_DIR}/.env.collector"), no secrets copied beyond DATABASE_URL)"

# ---- 4. image ----------------------------------------------------------------
docker image inspect "${BASE_IMAGE}" >/dev/null 2>&1 \
  || die "base image ${BASE_IMAGE} is not present on this host; pass --base-image <tag>"
log "building yance-collector:${RELEASE} from ${BASE_IMAGE} (no network needed)"
docker build \
  --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
  -f "${TARGET_DIR}/docker/Dockerfile.collector" \
  -t "yance-collector:${RELEASE}" "${TARGET_DIR}"

# ---- 5. smoke test -----------------------------------------------------------
log "smoke test: import worker + collector CLI"
docker run --rm --entrypoint python "yance-collector:${RELEASE}" -c \
  "import os; os.chdir('/app'); import app.workers.policy_collector as w, app.services.policy_collection.scheduler as s, app.services.policy_collection.keyword_search as k; print('worker imports OK')"

log "smoke test: volume directory ownership inside the image"
docker run --rm --entrypoint sh "yance-collector:${RELEASE}" -c \
  'stat -c "%U:%G %a %n" /app/policy_raw /app/policy_raw/attachments'

log "alembic head expected by this release"
docker run --rm --entrypoint alembic "yance-collector:${RELEASE}" heads

cat <<EOF

Installed: ${TARGET_DIR}
Image:     yance-collector:${RELEASE}

Nothing has been started.  Next steps (run from ${TARGET_DIR}):
  ./ops/collector.sh migrate-status     # read-only: production schema vs head
  ./ops/collector.sh trial 100          # bounded trial, writes evidence + rows
  ./ops/collector.sh start              # start the continuous loop
EOF
