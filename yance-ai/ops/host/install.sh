#!/usr/bin/env bash
# install.sh — one-shot, repeatable installer for the host-native policy collector.
#
# Guarantees, in the order they matter:
#   1. fail-fast: any error aborts immediately and says which step failed;
#   2. idempotent: running it twice leaves exactly one user, one venv with the same
#      dependency set, one set of systemd units, one logrotate rule, one cron-free
#      timer — no duplicates, no orphan units;
#   3. it never touches the website stack: it does not restart, rebuild, migrate or
#      reconfigure yance-prod-api-1 / yance-prod-db-1 / nginx;
#   4. it never prints the database password.
#
# Usage (on the server, as root):
#   sudo bash /root/yance-collector-host/install.sh                 # install, do not start
#   sudo bash /root/yance-collector-host/install.sh --start         # install and start
#   sudo bash /root/yance-collector-host/install.sh --stop-docker-collector
#
# Flags:
#   --start                     enable *and* start the service after install
#   --stop-docker-collector     stop the legacy docker collector if it is up (required
#                               when it is running: two collectors must never write)
#   --reinstall-venv            rebuild .venv from scratch even if it already works
#   --skip-deps                 reuse the existing .venv without touching pip
#   --rev <rev>                 collector revision directory suffix (default 20261106-r3)

set -Eeuo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SELF_DIR}/lib.sh"

START_SERVICE=0
STOP_DOCKER=0
REBUILD_VENV=0
SKIP_DEPS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) START_SERVICE=1; shift ;;
    --stop-docker-collector) STOP_DOCKER=1; shift ;;
    --reinstall-venv) REBUILD_VENV=1; shift ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
    --rev) COLLECTOR_REV="$2"; shift 2 ;;
    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done

# Re-derive the paths after a possible --rev override.
COLLECTOR_HOME="${COLLECTOR_BASE}/collector-${COLLECTOR_REV}"
COLLECTOR_VENV="${COLLECTOR_HOME}/.venv"
COLLECTOR_PY="${COLLECTOR_VENV}/bin/python"

require_root
require_cmd systemctl
require_cmd python3
require_cmd df

step "0/9 preflight"
require_layout
log "collector code: ${COLLECTOR_HOME}"
log "run user:       ${COLLECTOR_USER}"
log "state dir:      ${COLLECTOR_RAW_DIR}"
log "env file:       ${COLLECTOR_ENV_FILE}"

[[ "$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "3.12" ]] \
  || fail "host python is not 3.12 (project requires >=3.12,<3.14)"

free_root="$(disk_free_mb /opt)"
[[ "${free_root:-0}" -ge 3072 ]] || fail "less than 3 GB free on /opt (${free_root}MB): a venv plus evidence would fill the disk"

# The database is verified over TCP, not by asking docker: the collector is a plain
# host client and must keep working even if the docker CLI is unavailable. The port
# has to be loopback-only — a public database port would make the plan unsafe.
if ss -ltn 2>/dev/null | grep -qE "0\.0\.0\.0:${PG_HOST_PORT}|\[::\]:${PG_HOST_PORT}"; then
  fail "port ${PG_HOST_PORT} is published on all interfaces; refusing to proceed (loopback only)"
fi
ss -ltn 2>/dev/null | grep -q "127.0.0.1:${PG_HOST_PORT}" \
  || fail "nothing is listening on 127.0.0.1:${PG_HOST_PORT}; the production database is not up"
log "database port: ${PG_HOST_PORT} listening on loopback only"

# ---- legacy collector guard -------------------------------------------------
step "1/9 legacy collector check"
# Two collectors writing the same tables must never happen. Detection uses the docker
# CLI only when it exists; absence is a warning, not a failure.
if command -v docker >/dev/null 2>&1; then
  LEGACY_CONTAINER="$(docker ps -a --filter name=yance-collector --format '{{.Names}}' 2>/dev/null | head -1 || true)"
  if [[ -n "${LEGACY_CONTAINER}" ]]; then
    legacy_running="$(docker inspect -f '{{.State.Running}}' "${LEGACY_CONTAINER}" 2>/dev/null || echo false)"
    if [[ "${legacy_running}" == "true" ]]; then
      if [[ "${STOP_DOCKER}" -eq 1 ]]; then
        log "stopping legacy container ${LEGACY_CONTAINER} (kept for rollback, restart policy disabled)"
        docker update --restart=no "${LEGACY_CONTAINER}" >/dev/null
        docker stop --time 120 "${LEGACY_CONTAINER}" >/dev/null
      else
        fail "legacy docker collector ${LEGACY_CONTAINER} is RUNNING; two collectors would double-write. Re-run with --stop-docker-collector"
      fi
    else
      # Exited but could come back on reboot: pin it off, keep it for rollback.
      docker update --restart=no "${LEGACY_CONTAINER}" >/dev/null 2>&1 || true
      log "legacy container ${LEGACY_CONTAINER} present but stopped; restart policy disabled"
    fi
  else
    log "no legacy docker collector container"
  fi
else
  warn "docker CLI absent: skipping legacy container detection (verify by hand that no collector container runs)"
fi

if pgrep -af "app.workers.policy_collector" | grep -v "pgrep" >/dev/null 2>&1; then
  if systemctl is-active --quiet yance-collector; then
    log "collector service already active (this install will restart it at the end if --start)"
  else
    fail "a stray collector process is running outside systemd: $(pgrep -af 'app.workers.policy_collector' | head -3)"
  fi
fi

# ---- system packages --------------------------------------------------------
step "2/9 python venv support"
if python3 -c "import ensurepip" >/dev/null 2>&1; then
  log "ensurepip present"
else
  log "installing python3-venv via apt (one time)"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3-venv python3-dev >/dev/null
  python3 -c "import ensurepip" >/dev/null 2>&1 || fail "python3-venv installed but ensurepip still unavailable"
fi

# ---- user and directories ---------------------------------------------------
step "3/9 service user and persistent directories"
if id -u "${COLLECTOR_USER}" >/dev/null 2>&1; then
  log "user ${COLLECTOR_USER} exists"
else
  useradd --system --home-dir "${COLLECTOR_STATE_DIR}" --no-create-home \
          --shell /usr/sbin/nologin --comment "yance policy collector" "${COLLECTOR_USER}"
  log "created system user ${COLLECTOR_USER} (nologin, no home shell)"
fi

install -d -m 0750 -o "${COLLECTOR_USER}" -g "${COLLECTOR_USER}" "${COLLECTOR_STATE_DIR}"
install -d -m 0750 -o "${COLLECTOR_USER}" -g "${COLLECTOR_USER}" "${COLLECTOR_RAW_DIR}"
install -d -m 0750 -o "${COLLECTOR_USER}" -g "${COLLECTOR_USER}" "${COLLECTOR_RAW_DIR}/attachments"
install -d -m 0750 -o "${COLLECTOR_USER}" -g adm "${COLLECTOR_LOG_DIR}"
install -d -m 0750 -o root -g "${COLLECTOR_USER}" "${COLLECTOR_ETC_DIR}"
log "directories ready (${COLLECTOR_RAW_DIR} persists raw evidence across reinstalls)"
# A stale PAUSED flag from a previous experiment would silently disable collection.
if [[ -f "${COLLECTOR_RAW_DIR}/PAUSED" ]]; then
  warn "found existing PAUSED flag: $(head -c 200 "${COLLECTOR_RAW_DIR}/PAUSED")"
  warn "collection stays paused until you run: yance-collector resume"
fi

# ---- environment file -------------------------------------------------------
step "4/9 collector environment (derived, least privilege)"
python3 "${SELF_DIR}/py/write_env.py" \
  --prod-env "${PROD_ENV_FILE}" \
  --out "${COLLECTOR_ENV_FILE}" \
  --pg-host 127.0.0.1 \
  --pg-port "${PG_HOST_PORT}" \
  --raw-dir "${COLLECTOR_RAW_DIR}" \
  --catalog-dir "${COLLECTOR_HOME}/config/policy_sources"
chown root:"${COLLECTOR_USER}" "${COLLECTOR_ENV_FILE}"
chmod 0640 "${COLLECTOR_ENV_FILE}"
log "env written: $(db_url_fingerprint)"

# ---- virtualenv -------------------------------------------------------------
step "5/9 isolated virtualenv"
venv_ok=0
if [[ -x "${COLLECTOR_PY}" && "${REBUILD_VENV}" -eq 0 ]]; then
  if ( cd "${COLLECTOR_HOME}" && "${COLLECTOR_PY}" -c "import app.workers.policy_collector" >/dev/null 2>&1 ); then
    venv_ok=1
    log "existing venv imports the worker; reusing it"
  else
    warn "existing venv is present but cannot import the worker; rebuilding"
  fi
fi

if [[ "${venv_ok}" -eq 0 ]]; then
  if [[ -d "${COLLECTOR_VENV}" ]]; then
    mv "${COLLECTOR_VENV}" "${COLLECTOR_VENV}.old.$(date +%s)"
  fi
  python3 -m venv "${COLLECTOR_VENV}"
  log "venv created at ${COLLECTOR_VENV}"
fi

if [[ "${SKIP_DEPS}" -eq 0 ]]; then
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  export PIP_NO_INPUT=1
  "${COLLECTOR_PY}" -m pip install --quiet --upgrade pip setuptools wheel \
    || fail "pip bootstrap failed (no package index reachable from this host?)"
  # The deployed tree is a release tarball with no pyproject.toml, so dependencies
  # come from an explicit, auditable list rather than an editable project install.
  install -m 0644 "${SELF_DIR}/collector-requirements.txt" "${COLLECTOR_HOME}/collector-requirements.txt"
  log "installing collector dependencies (slow step, ~2-4 min)"
  "${COLLECTOR_PY}" -m pip install --quiet -r "${SELF_DIR}/collector-requirements.txt" \
    || fail "dependency install failed; the venv was left in place for inspection"
  log "dependencies installed"
else
  log "dependency install skipped (--skip-deps)"
fi

( cd "${COLLECTOR_HOME}" && "${COLLECTOR_PY}" -c "import app.workers.policy_collector" >/dev/null ) \
  || fail "worker entry does not import with this venv"
( cd "${COLLECTOR_HOME}" && "${COLLECTOR_PY}" -c "import psycopg, sqlalchemy, alembic, pgvector" >/dev/null ) \
  || fail "core database dependencies missing from venv"
log "venv sanity: worker entry + psycopg + sqlalchemy + alembic + pgvector OK"

# The service user must be able to run the venv but never write to it.
chown -R root:root "${COLLECTOR_VENV}"
chmod -R a+rX "${COLLECTOR_VENV}"
chown -R root:root "${COLLECTOR_HOME}/app" 2>/dev/null || true
log "venv locked to read-only for ${COLLECTOR_USER}"

# ---- units, timer, logrotate, control script --------------------------------
step "6/9 systemd units, guard timer, log rotation"
install -m 0644 "${SELF_DIR}/systemd/yance-collector.service"        /etc/systemd/system/yance-collector.service
install -m 0644 "${SELF_DIR}/systemd/yance-collector-guard.service"  /etc/systemd/system/yance-collector-guard.service
install -m 0644 "${SELF_DIR}/systemd/yance-collector-guard.timer"    /etc/systemd/system/yance-collector-guard.timer
install -m 0755 "${SELF_DIR}/guard.sh"                               /usr/local/bin/yance-collector-guard
install -m 0755 "${SELF_DIR}/collectorctl.sh"                        /usr/local/bin/yance-collector
install -m 0755 "${SELF_DIR}/verify-isolated.sh"                     /usr/local/bin/yance-collector-verify-isolated
install -m 0644 "${SELF_DIR}/logrotate/yance-collector"              /etc/logrotate.d/yance-collector

# Helper python used by `yance-collector env` and `yance-collector verify-web`.
install -d -m 0755 /usr/local/lib/yance-collector
install -m 0644 "${SELF_DIR}/py/write_env.py"  /usr/local/lib/yance-collector/write_env.py
install -m 0644 "${SELF_DIR}/py/verify_web.py" /usr/local/lib/yance-collector/verify_web.py
log "control script: /usr/local/bin/yance-collector (+ verify-isolated, helpers in /usr/local/lib/yance-collector)"

systemctl daemon-reload
systemctl enable yance-collector.service >/dev/null
systemctl enable --now yance-collector-guard.timer >/dev/null
logrotate -d /etc/logrotate.d/yance-collector >/dev/null 2>&1 \
  || fail "logrotate config rejected; refusing to report success"
log "units installed, service enabled, guard timer active"

# Exactly one copy of each unit must exist — catch leftovers from earlier attempts.
dup="$(systemctl list-unit-files 'yance-collector*' --no-legend | awk '{print $1}' | sort | uniq -d || true)"
[[ -z "${dup}" ]] || fail "duplicate collector units installed: ${dup}"

# ---- database reachability (read-only) --------------------------------------
step "7/9 database connectivity (read-only)"
"${COLLECTOR_PY}" - "${COLLECTOR_ENV_FILE}" <<'PY' || fail "collector cannot reach the production database over loopback"
import sys, urllib.parse, psycopg
url = None
for line in open(sys.argv[1], encoding="utf-8"):
    if line.startswith("DATABASE_URL="):
        url = line.split("=", 1)[1].strip()
        break
if not url:
    print("no DATABASE_URL in env", file=sys.stderr); sys.exit(3)
parts = urllib.parse.urlsplit(url)
dsn = f"host={parts.hostname} port={parts.port} dbname={parts.path.lstrip('/')} user={urllib.parse.unquote(parts.username or '')} password={urllib.parse.unquote(parts.password or '')} connect_timeout=10"
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("select current_database(), (select version_num from alembic_version)")
        db, rev = cur.fetchone()
print(f"connected db={db} alembic={rev}")
PY

alembic_now="$("${COLLECTOR_PY}" - "${COLLECTOR_ENV_FILE}" <<'PY'
import sys, urllib.parse, psycopg
for line in open(sys.argv[1], encoding="utf-8"):
    if line.startswith("DATABASE_URL="):
        url = line.split("=", 1)[1].strip(); break
p = urllib.parse.urlsplit(url)
dsn = f"host={p.hostname} port={p.port} dbname={p.path.lstrip('/')} user={urllib.parse.unquote(p.username or '')} password={urllib.parse.unquote(p.password or '')} connect_timeout=10"
with psycopg.connect(dsn) as conn, conn.cursor() as cur:
    cur.execute("select version_num from alembic_version")
    print(cur.fetchone()[0])
PY
)"
alembic_head="$( cd "${COLLECTOR_HOME}" && "${COLLECTOR_PY}" -m alembic heads 2>/dev/null | awk '{print $1}' | head -1 )"
log "alembic: current=${alembic_now} head=${alembic_head}"

# ---- optional start ---------------------------------------------------------
step "8/9 service start"
if [[ "${START_SERVICE}" -eq 1 ]]; then
  if [[ "${alembic_now}" != "${alembic_head}" ]]; then
    fail "refusing to start: database is at ${alembic_now}, code head is ${alembic_head}. Run: yance-collector migrate --yes"
  fi
  systemctl restart yance-collector.service
  sleep 8
  systemctl is-active --quiet yance-collector.service \
    || fail "service failed to stay up; see: journalctl -u yance-collector -n 100"
  log "service running"
else
  log "service installed and enabled, NOT started (database must be migrated first)"
  log "after a confirmed migration run: systemctl start yance-collector"
fi

# ---- summary ---------------------------------------------------------------
step "9/9 summary"
cat <<EOF

  code tree      : ${COLLECTOR_HOME}
  venv           : ${COLLECTOR_VENV}  (root-owned, ${COLLECTOR_USER} read-only)
  run user       : ${COLLECTOR_USER}  (system, nologin)
  env file       : ${COLLECTOR_ENV_FILE}  (0640 root:${COLLECTOR_USER})
  raw evidence   : ${COLLECTOR_RAW_DIR}  (persistent)
  logs           : ${COLLECTOR_LOG_DIR}/collector.log  (logrotate daily, 14 kept)
  service        : yance-collector.service   $([ "${START_SERVICE}" -eq 1 ] && echo running || echo "enabled, stopped")
  guard timer    : yance-collector-guard.timer  $(systemctl is-active yance-collector-guard.timer)
  control script : /usr/local/bin/yance-collector

  next:
    yance-collector status          # unit + heartbeat + last cycle
    yance-collector progress        # backfill cursors, no page-1 loop
    yance-collector pause "reason"  # stop scheduling without stopping the unit
    yance-collector resume

EOF
