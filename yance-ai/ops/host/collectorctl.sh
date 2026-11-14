#!/usr/bin/env bash
# yance-collector — the only operator entry point for the host-native collector.
#
# Deliberate design points:
#   * no `docker compose`, no `docker run`, no container exec for anything the
#     collector does: it is a host process and its commands run on the host;
#   * the only optional docker use is `docker ps` to *detect* a legacy container —
#     and it degrades to a warning if the CLI is absent;
#   * reads are read-only; state changes are limited to start/stop/restart,
#     pause/resume, env regeneration and `migrate --yes`.

set -Euo pipefail

ENV_FILE="/etc/yance/collector.env"
HOME_DIR="${COLLECTOR_HOME:-/opt/yance/collector-20261106-r3}"
VENV_PY="${HOME_DIR}/.venv/bin/python"
CLI="${HOME_DIR}/scripts/policy_collection/cli.py"
RAW_DIR="/var/lib/yance/policy_raw"
LOG_DIR="/var/log/yance"
SERVICE="yance-collector"
RUN_USER="yancecoll"
PG_HOST="127.0.0.1"
PG_PORT="5434"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
warn() { printf 'warn: %s\n' "$*" >&2; }
need_root() { [[ ${EUID} -eq 0 ]] || die "run as root: sudo yance-collector ${CMD}"; }

load_env() {
  [[ -r "${ENV_FILE}" ]] || die "missing ${ENV_FILE}; run install.sh first"
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  set +a
}

# Collection commands run as the service user: it owns the raw evidence tree, and
# running as root would leave files the service can no longer write.
as_collector() {
  runuser -u "${RUN_USER}" -- /bin/bash -c '
    set -a; . "'"${ENV_FILE}"'"; set +a
    cd "'"${HOME_DIR}"'"
    exec "$@"
  ' _ "$@"
}

port_open() { ss -ltn 2>/dev/null | grep -q "127.0.0.1:${PG_PORT}"; }

cmd_help() {
  cat <<'EOF'
yance-collector <command>

  status                 unit state, heartbeat, disk floor, pause flag, tail of log
  progress               backfill cursor per source + coverage + alerts (read-only)
  doctor                 self-check: paths, permissions, units, DB, disk, legacy process
  logs [-f] [n]          tail collector log (default 80)
  heartbeat              raw heartbeat JSON
  trial [n]              collect n national sources now (real writes, rate limited)
  backfill [opts]        one bounded history batch: --pages N --docs N --sources a,b
  run-once               one incremental cycle then exit (same code path as service)
  start | stop | restart unit control
  pause ["reason"]       write PAUSED; the running process obeys at the next cycle
  resume                 remove PAUSED
  migrate-status         current vs head revision (read-only)
  migrate --yes          alembic upgrade head (dumps the DB first)
  env                    regenerate /etc/yance/collector.env from .env.prod
  verify-web [query]     prove a normal user can retrieve collected text through the API
EOF
}

cmd_status() {
  need_root
  printf '== unit ==\n'
  systemctl is-enabled "${SERVICE}" >/dev/null 2>&1 && en="enabled" || en="$(systemctl is-enabled ${SERVICE} 2>&1 | head -1)"
  systemctl is-active "${SERVICE}" >/dev/null 2>&1 && ac="active" || ac="inactive"
  printf '  enabled=%s active=%s\n' "${en}" "${ac}"
  systemctl show "${SERVICE}" -p NRestarts -p ActiveEnterTimestamp -p ExecMainPID --no-pager | sed 's/^/  /'

  printf '\n== heartbeat ==\n'
  if [[ -f "${RAW_DIR}/collector_state.json" ]]; then
    python3 - "${RAW_DIR}/collector_state.json" <<'PY'
import json, sys
from datetime import datetime, UTC
path = sys.argv[1]
try:
    d = json.load(open(path, encoding="utf-8"))
except Exception as exc:
    print(f"  unreadable: {exc}"); raise SystemExit(0)
last = d.get("last_cycle_at")
print(f"  last_cycle_at : {last}")
if last:
    try:
        dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        age = int((datetime.now(UTC) - dt).total_seconds())
        print(f"  age           : {age}s {'(STALE)' if age > 4500 else ''}")
    except ValueError:
        pass
for key in ("status", "stop_reason", "ran", "skipped", "cycle_index", "last_error", "storage", "updated_at"):
    if key in d:
        print(f"  {key:<14}: {d[key]}")
PY
  else
    echo "  absent (no cycle completed yet)"
  fi

  printf '\n== pause flag ==\n'
  if [[ -f "${RAW_DIR}/PAUSED" ]]; then
    printf '  PAUSED: %s\n' "$(head -c 300 "${RAW_DIR}/PAUSED")"
  else
    echo '  not paused'
  fi

  printf '\n== disk ==\n'
  local free floor
  free="$(df -Pm "${RAW_DIR}" | awk 'NR==2 {print $4}')"
  floor="${POLICY_COLLECTION_MIN_FREE_DISK_MB:-3000}"
  printf '  free=%sMB floor=%sMB -> %s\n' "${free}" "${floor}" \
    "$([[ ${free} -ge ${floor} ]] && echo ok || echo BELOW_FLOOR)"
  printf '  raw evidence: %s  (%s)\n' "${RAW_DIR}" "$(du -sh "${RAW_DIR}" 2>/dev/null | awk '{print $1}')"

  printf '\n== last log lines ==\n'
  tail -n 6 "${LOG_DIR}/collector.log" 2>/dev/null | sed 's/^/  /' || echo '  (none)'
  printf '\n== guard (last 3) ==\n'
  tail -n 3 "${LOG_DIR}/guard.log" 2>/dev/null | sed 's/^/  /' || echo '  (none)'
}

cmd_progress() {
  need_root; load_env
  port_open || die "database not reachable on ${PG_HOST}:${PG_PORT}"
  echo '-- backfill cursors (a stuck cursor would show the same page every time) --'
  as_collector "${VENV_PY}" "${CLI}" backfill-status || true
  echo
  echo '-- scheduler / runs --'
  as_collector "${VENV_PY}" "${CLI}" status || true
  echo
  echo '-- alerts --'
  as_collector "${VENV_PY}" "${CLI}" alerts || true
}

cmd_heartbeat() {
  [[ -f "${RAW_DIR}/collector_state.json" ]] || die 'no heartbeat file'
  python3 -m json.tool "${RAW_DIR}/collector_state.json"
}

cmd_logs() {
  local follow=0 lines=80
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f) follow=1; shift ;;
      *) lines="$1"; shift ;;
    esac
  done
  local files=("${LOG_DIR}/collector.log" "${LOG_DIR}/collector.err.log")
  if [[ "${follow}" -eq 1 ]]; then tail -n "${lines}" -F "${files[@]}"; else tail -n "${lines}" "${files[@]}" 2>/dev/null || echo "no logs in ${LOG_DIR}"; fi
}

cmd_run_once() { need_root; load_env; as_collector "${VENV_PY}" -m app.workers.policy_collector --once; }

cmd_trial() {
  need_root; load_env
  local n="${1:-2}"
  [[ "${n}" =~ ^[0-9]+$ ]] || die 'trial takes a number of sources'
  echo "collecting up to ${n} national sources (real writes, rate limited)…"
  as_collector "${VENV_PY}" "${CLI}" run --level national --limit "${n}" --trigger manual-trial
}

cmd_backfill() { need_root; load_env; as_collector "${VENV_PY}" "${CLI}" backfill-run --enable-collection "$@"; }

cmd_pause() {
  need_root
  local reason="${1:-paused by operator via yance-collector}"
  install -d -m 0750 -o "${RUN_USER}" -g "${RUN_USER}" "${RAW_DIR}"
  printf 'operator: %s at %s\n' "${reason}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"${RAW_DIR}/PAUSED"
  chown "${RUN_USER}:${RUN_USER}" "${RAW_DIR}/PAUSED"; chmod 0640 "${RAW_DIR}/PAUSED"
  echo "paused: ${reason}"
  echo 'the running process stops at the next cycle boundary; no restart needed'
}

cmd_resume() {
  need_root
  if [[ -f "${RAW_DIR}/PAUSED" ]]; then
    local content; content="$(head -c 200 "${RAW_DIR}/PAUSED")"
    rm -f "${RAW_DIR}/PAUSED"; echo "resumed (removed: ${content})"
  else
    echo 'not paused; nothing to do'
  fi
}

cmd_restart() { need_root; systemctl restart "${SERVICE}"; sleep 5; systemctl is-active --quiet "${SERVICE}" || die "restart failed: journalctl -u ${SERVICE} -n 80"; echo restarted; }
cmd_stop()    { need_root; systemctl stop "${SERVICE}"; echo 'stopped (enable state unchanged)'; }
cmd_start()   { need_root; systemctl start "${SERVICE}"; sleep 5; systemctl is-active --quiet "${SERVICE}" || die "start failed: journalctl -u ${SERVICE} -n 80"; echo started; }

cmd_migrate_status() {
  need_root; load_env; cd "${HOME_DIR}"
  echo "current: $("${VENV_PY}" -m alembic current 2>&1 | tail -2)"
  echo "head   : $("${VENV_PY}" -m alembic heads 2>&1 | tail -2)"
}

# Logical backup without assuming docker: host pg_dump first, container exec only
# as a fallback when the host has no client and docker is present.
dump_database() {
  local out="$1"
  install -d -m 0700 /opt/yance/backups
  if command -v pg_dump >/dev/null 2>&1; then
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
      -h "${PG_HOST}" -p "${PG_PORT}" -U "${POSTGRES_USER:-yance}" -Fc \
      -d "${POSTGRES_DB:-yance_prod}" >"${out}"
  elif command -v docker >/dev/null 2>&1; then
    warn 'host pg_dump absent; falling back to docker exec (install postgresql-client to avoid this)'
    docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" yance-prod-db-1 \
      pg_dump -U "${POSTGRES_USER:-yance}" -Fc -d "${POSTGRES_DB:-yance_prod}" >"${out}"
  else
    die 'no pg_dump on the host and no docker CLI: cannot take a pre-migration backup'
  fi
  [[ -s "${out}" ]] || die 'backup dump is empty; aborting before touching the schema'
  chmod 0600 "${out}"
}

cmd_migrate() {
  need_root
  [[ "${1:-}" == "--yes" ]] || die 'refusing to migrate without --yes (this changes the production schema)'
  load_env
  local stamp out
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  out="/opt/yance/backups/pre-migrate-policy-${stamp}.dump"
  echo "dumping database to ${out} (password never on the command line)…"
  dump_database "${out}"
  echo "dump ok: $(du -h "${out}" | awk '{print $1}')"
  cd "${HOME_DIR}"
  "${VENV_PY}" -m alembic upgrade head
  echo "now at: $("${VENV_PY}" -m alembic current 2>&1 | tail -1)"
  echo "rollback target if needed: ${out}"
}

cmd_env() {
  need_root
  local helper='/usr/local/lib/yance-collector/write_env.py'
  [[ -f "${helper}" ]] || die "missing ${helper}; rerun install.sh"
  python3 "${helper}" \
    --prod-env /opt/yance/yance-ai/.env.prod \
    --out "${ENV_FILE}" \
    --pg-host "${PG_HOST}" --pg-port "${PG_PORT}" \
    --raw-dir "${RAW_DIR}" \
    --catalog-dir "${HOME_DIR}/config/policy_sources"
  chown root:"${RUN_USER}" "${ENV_FILE}"; chmod 0640 "${ENV_FILE}"
  echo 'env regenerated; apply with: yance-collector restart'
}

cmd_verify_web() {
  need_root
  local helper='/usr/local/lib/yance-collector/verify_web.py'
  [[ -f "${helper}" ]] || die "missing ${helper}; rerun install.sh"
  # Arguments are passed through verbatim so --token/--email/--json/--limit/--base-url
  # all reach argparse instead of being swallowed as the query string.
  if [[ $# -eq 0 ]]; then
    set -- --query=知识产权
  fi
  "${VENV_PY}" "${helper}" "$@"
}

cmd_doctor() {
  need_root; load_env
  local fail=0
  chk() { printf '  %-40s %s\n' "$1" "$2"; [[ "${3:-}" == FAIL ]] && fail=1 || true; }

  echo '== filesystem and identity =='
  [[ -d "${HOME_DIR}" ]] && chk 'code tree' 'ok' || chk 'code tree' "MISSING ${HOME_DIR}" FAIL
  [[ -x "${VENV_PY}" ]] && chk 'venv python' 'ok' || chk 'venv python' MISSING FAIL
  id -u "${RUN_USER}" >/dev/null 2>&1 && chk 'service user' "ok (${RUN_USER})" || chk 'service user' MISSING FAIL
  runuser -u "${RUN_USER}" -- test -r "${ENV_FILE}" && chk "env readable by ${RUN_USER}" ok || chk "env readable by ${RUN_USER}" FAIL FAIL
  runuser -u "${RUN_USER}" -- test -w "${RAW_DIR}" && chk "raw dir writable by ${RUN_USER}" ok || chk "raw dir writable by ${RUN_USER}" FAIL FAIL
  local mode; mode="$(stat -c '%a %U:%G' "${ENV_FILE}" 2>/dev/null || echo missing)"
  [[ "${mode}" == "640 root:${RUN_USER}" ]] && chk 'env permissions' "${mode}" || chk 'env permissions' "${mode} (want 640 root:${RUN_USER})" FAIL
  chk 'ping the venv as the service user' \
    "$(runuser -u "${RUN_USER}" -- "${VENV_PY}" -c 'import app.workers.policy_collector; print("import ok")' 2>&1 | tail -1)"

  echo '== units =='
  systemctl is-enabled --quiet "${SERVICE}" && chk 'service enabled' ok || chk 'service enabled' 'not enabled' FAIL
  systemctl is-active --quiet "${SERVICE}" && chk 'service active' ok || chk 'service active' 'inactive'
  systemctl is-active --quiet yance-collector-guard.timer && chk 'guard timer active' ok || chk 'guard timer active' inactive FAIL
  logrotate -d /etc/logrotate.d/yance-collector >/dev/null 2>&1 && chk 'logrotate config' valid || chk 'logrotate config' INVALID FAIL
  local dup; dup="$(systemctl list-unit-files 'yance-collector*' --no-legend | awk '{print $1}' | sort | uniq -d)"
  [[ -z "${dup}" ]] && chk 'no duplicate units' ok || chk 'no duplicate units' "${dup}" FAIL

  echo '== runtime =='
  local free; free="$(df -Pm "${RAW_DIR}" | awk 'NR==2 {print $4}')"
  [[ ${free} -ge 3072 ]] && chk 'disk free' "${free}MB" || chk 'disk free' "${free}MB low" FAIL
  port_open && chk 'database reachable on loopback' "${PG_HOST}:${PG_PORT}" || chk 'database reachable on loopback' 'no listener' FAIL
  ss -ltn | grep -qE "0\.0\.0\.0:${PG_PORT}" && chk 'database not public' 'EXPOSED' FAIL || chk 'database not public' 'loopback only'
  local procs; procs="$(pgrep -cf 'app.workers.policy_collector' || true)"
  chk 'collector processes' "${procs} python process(es)"
  if command -v docker >/dev/null 2>&1; then
    local legacy; legacy="$(docker ps --filter name=yance-collector --format '{{.Names}}' 2>/dev/null | head -1)"
    [[ -z "${legacy}" ]] && chk 'no legacy docker collector' ok || chk 'no legacy docker collector' "RUNNING ${legacy}" FAIL
  else
    chk 'no legacy docker collector' 'skipped (no docker CLI)'
  fi
  [[ -f "${RAW_DIR}/PAUSED" ]] && chk 'pause flag' "PAUSED: $(head -c 60 "${RAW_DIR}/PAUSED")" || chk 'pause flag' 'not paused'

  echo
  [[ "${fail}" -eq 0 ]] && echo 'doctor: all blocking checks passed' || { echo 'doctor: blocking checks failed' >&2; exit 1; }
}

CMD="${1:-help}"; shift || true
case "${CMD}" in
  status)         cmd_status "$@" ;;
  progress)       cmd_progress "$@" ;;
  heartbeat)      cmd_heartbeat "$@" ;;
  doctor)         cmd_doctor "$@" ;;
  logs)           cmd_logs "$@" ;;
  trial)          cmd_trial "$@" ;;
  backfill)       cmd_backfill "$@" ;;
  run-once)       cmd_run_once "$@" ;;
  pause)          cmd_pause "$@" ;;
  resume)         cmd_resume "$@" ;;
  restart)        cmd_restart "$@" ;;
  stop)           cmd_stop "$@" ;;
  start)          cmd_start "$@" ;;
  migrate-status) cmd_migrate_status "$@" ;;
  migrate)        cmd_migrate "$@" ;;
  env)            cmd_env "$@" ;;
  verify-web)     cmd_verify_web "$@" ;;
  help|-h|--help) cmd_help ;;
  *) die "unknown command '${CMD}' (try: yance-collector help)" ;;
esac
