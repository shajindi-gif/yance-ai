#!/usr/bin/env bash
# Shared helpers for the host-native policy collector (no Docker at runtime).
#
# Hard rules encoded here:
#  * every failure stops the script (fail-fast), nothing is silently skipped;
#  * no secret is ever echoed: DATABASE_URL is assembled in Python and written
#    straight to a 0600 file, never printed, never put in argv;
#  * every path used is a path that actually exists on this host — no /app,
#    no `docker compose`, no invented users.

set -Eeuo pipefail

HOST_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HOST_LIB_DIR

# ---- fixed layout -----------------------------------------------------------
COLLECTOR_REV="${COLLECTOR_REV:-20261106-r3}"
COLLECTOR_BASE="${COLLECTOR_BASE:-/opt/yance}"
COLLECTOR_HOME="${COLLECTOR_BASE}/collector-${COLLECTOR_REV}"
COLLECTOR_USER="${COLLECTOR_USER:-yancecoll}"
COLLECTOR_STATE_DIR="${COLLECTOR_STATE_DIR:-/var/lib/yance}"
COLLECTOR_RAW_DIR="${COLLECTOR_RAW_DIR:-${COLLECTOR_STATE_DIR}/policy_raw}"
COLLECTOR_LOG_DIR="${COLLECTOR_LOG_DIR:-/var/log/yance}"
COLLECTOR_ETC_DIR="${COLLECTOR_ETC_DIR:-/etc/yance}"
COLLECTOR_ENV_FILE="${COLLECTOR_ENV_FILE:-${COLLECTOR_ETC_DIR}/collector.env}"
COLLECTOR_VENV="${COLLECTOR_VENV:-${COLLECTOR_HOME}/.venv}"
COLLECTOR_PY="${COLLECTOR_VENV}/bin/python"
COLLECTOR_CLI_ENTRY="${COLLECTOR_HOME}/scripts/policy_collection/cli.py"
COLLECTOR_LOCK="${COLLECTOR_LOCK:-/run/yance-collector.lock}"
PROD_ENV_FILE="${PROD_ENV_FILE:-/opt/yance/yance-ai/.env.prod}"
PG_CONTAINER="${PG_CONTAINER:-yance-prod-db-1}"
PG_HOST_PORT="${PG_HOST_PORT:-5434}"
PROD_API_BASE="${PROD_API_BASE:-http://127.0.0.1:8000}"

# ---- logging ----------------------------------------------------------------
if [[ -t 1 ]]; then
  _c_red=$'\033[31m'; _c_grn=$'\033[32m'; _c_yel=$'\033[33m'; _c_off=$'\033[0m'
else
  _c_red=''; _c_grn=''; _c_yel=''; _c_off=''
fi

log()   { printf '%s[host-collector]%s %s\n' "$_c_grn" "$_c_off" "$*"; }
warn()  { printf '%s[host-collector] WARN%s %s\n' "$_c_yel" "$_c_off" "$*" >&2; }
fail()  { printf '%s[host-collector] FAIL%s %s\n' "$_c_red" "$_c_off" "$*" >&2; exit 1; }

step()  { printf '\n%s== %s ==%s\n' "$_c_grn" "$*" "$_c_off"; }

on_error() {
  local rc=$? line=${1:-?}
  printf '%s[host-collector] FAIL%s aborted at line %s (exit %s)\n' \
    "$_c_red" "$_c_off" "$line" "$rc" >&2
  printf '%s[host-collector] FAIL%s nothing after this point ran; rerun the same command to continue (idempotent)\n' \
    "$_c_red" "$_c_off" >&2
}
trap 'on_error $LINENO' ERR

# ---- preconditions ----------------------------------------------------------
require_root() {
  [[ ${EUID} -eq 0 ]] || fail "must run as root (use: sudo bash $0 ...)"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

# The collector must never point at a path that does not exist on this host.
require_layout() {
  [[ -d "${COLLECTOR_HOME}" ]] || fail "collector code tree missing: ${COLLECTOR_HOME}"
  [[ -f "${COLLECTOR_HOME}/app/workers/policy_collector.py" ]] \
    || fail "collector worker entry missing: ${COLLECTOR_HOME}/app/workers/policy_collector.py"
  [[ -d "${COLLECTOR_HOME}/config/policy_sources" ]] \
    || fail "source catalog missing: ${COLLECTOR_HOME}/config/policy_sources"
  [[ -f "${PROD_ENV_FILE}" ]] || fail "production env file missing: ${PROD_ENV_FILE}"
}

# ---- systemd / runtime helpers ---------------------------------------------
svc_state() { systemctl is-active --quiet "$1" && echo active || echo inactive; }

# Read the DATABASE_URL the collector will use, without ever printing it.
db_url_fingerprint() {
  if [[ -r "${COLLECTOR_ENV_FILE}" ]]; then
    python3 - "${COLLECTOR_ENV_FILE}" <<'PY'
import sys, urllib.parse
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if line.startswith("DATABASE_URL="):
        u = urllib.parse.urlsplit(line.split("=", 1)[1])
        print(f"{u.hostname or '?'}:{u.port or '?'}{u.path or ''} user={u.username or '?'} password={'set' if u.password else 'unset'}")
        break
else:
    print("DATABASE_URL absent")
PY
  else
    echo "env file absent"
  fi
}

disk_free_mb() {
  df -Pm "$1" 2>/dev/null | awk 'NR==2 {print $4}'
}
