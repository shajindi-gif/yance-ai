#!/usr/bin/env bash
# One entry point for collector operations on the server.
#
# Everything here is a thin, honest wrapper over the CLI that already exists
# (`scripts/policy_collection/cli.py` and `python -m app.workers.policy_collector`).
# It exists so that an on-call engineer under pressure does not have to remember
# five different argument shapes — and so that the risky commands are spelled out
# rather than improvised.
#
# IMPORTANT — this script runs on the *server*, where there is no .venv and the
# repository is not a git checkout.  Every Python command therefore executes inside
# the collector container, never on the host.  That is the difference from the
# previous revision of this file, which assumed a developer laptop layout.
#
# Usage:
#   ./ops/collector.sh status              # container health, heartbeat, recent runs
#   ./ops/collector.sh progress            # backfill cursors + searchable counts
#   ./ops/collector.sh start               # start the collector (never touches api/db)
#   ./ops/collector.sh stop                # stop it (in-flight document finishes)
#   ./ops/collector.sh restart             # stop + start
#   ./ops/collector.sh pause [reason]      # keep it running, download nothing
#   ./ops/collector.sh resume              # lift the pause
#   ./ops/collector.sh trial 100           # bounded trial batch of ~N documents
#   ./ops/collector.sh retry <source_id>   # re-read one source
#   ./ops/collector.sh reset <source_id>   # clear a parked/stuck cursor
#   ./ops/collector.sh alerts              # persistent failures + page gaps
#   ./ops/collector.sh logs [n]            # last n log lines (default 200)
#   ./ops/collector.sh backup [dir]        # pg_dump + raw evidence tarball
#   ./ops/collector.sh migrate-status      # READ ONLY: schema current vs head
#   ./ops/collector.sh migrate --yes       # explicit additive migration (see runbook)
#   ./ops/collector.sh rollback <image>    # re-pin the collector image, nothing else
#
# Requires: docker compose v2 on the host, and .env.collector generated once by
# ops/collector-install.sh (it contains only the whitelisted variables).

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${APP_DIR}/docker-compose.collector.yml"
ENV_FILE="${APP_DIR}/.env.collector"
PROD_COMPOSE="${APP_DIR}/docker-compose.prod.yml"
COLLECTOR_IMAGE="${COLLECTOR_IMAGE:-yance-collector:20261106-r3}"
BASE_IMAGE="${COLLECTOR_BASE_IMAGE:-yance-backend:web-auth-20261031-01}"
RAW_VOLUME="yance_policy_raw_prod"
APP_NETWORK="yance-prod_default"

die() { echo "error: $*" >&2; exit 1; }

dc() { docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" "$@"; }

need_env() {
  [[ -f "${ENV_FILE}" ]] || die "missing ${ENV_FILE}; run ops/collector-install.sh first"
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" config >/dev/null \
    || die "compose file is invalid"
}

need_image() {
  docker image inspect "${COLLECTOR_IMAGE}" >/dev/null 2>&1 \
    || die "image ${COLLECTOR_IMAGE} not found; run ops/collector-install.sh"
}

is_running() {
  dc ps --status running --format '{{.Service}}' 2>/dev/null | grep -qx collector
}

# Run a Python module inside the collector container.  Uses `exec` when the worker is
# up (fast, shares its environment) and a one-shot `run` when it is not (trial, reset,
# alerts are all valid while the loop is stopped).
in_collector() {
  if is_running; then
    dc exec -T collector python "$@"
  else
    dc run --rm --no-deps -T --entrypoint python collector "$@"
  fi
}

# Read something out of the raw-evidence volume without a running worker.  The volume
# is owned by uid 999 inside the image, so the helper runs as that uid.
in_volume() {
  local script="$1"; shift
  docker run --rm --user 999:999 -v "${RAW_VOLUME}":/data --entrypoint sh \
    "${COLLECTOR_IMAGE}" -c "${script}" "$@"
}

cmd_status() {
  need_env
  local health
  echo "== collector container =="
  dc ps || true
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$(dc ps -q collector 2>/dev/null | head -1)" 2>/dev/null || echo absent)"
  echo "health: ${health}"
  echo
  echo "== heartbeat =="
  if docker volume inspect "${RAW_VOLUME}" >/dev/null 2>&1; then
    in_volume 'ls -l /data 2>/dev/null | head -20; echo "--- state ---"; cat /data/collector_state.json 2>/dev/null || echo "no state file yet"; echo; echo "--- pause flag ---"; cat /data/PAUSED 2>/dev/null || echo "not paused"' || true
  else
    echo "volume ${RAW_VOLUME} does not exist yet (nothing collected)"
  fi
  echo
  echo "== database backlog =="
  need_image
  in_collector scripts/policy_collection/cli.py status || true
}

cmd_progress() {
  need_env
  need_image
  in_collector scripts/policy_collection/cli.py backfill-status || true
  echo
  in_collector scripts/policy_collection/cli.py backlog || true
  echo
  in_collector -c 'from app.core.db import SessionLocal
from app.services.policy_collection.keyword_search import searchable_counts
db = SessionLocal()
try:
    print("searchable corpus:", searchable_counts(db))
finally:
    db.close()'
}

cmd_start() {
  need_env
  need_image
  # Only the collector is started.  The database, api, migrate and agent-worker
  # services belong to the app stack and are never started, restarted or rebuilt here:
  # a collector must not be able to bounce production auth traffic.
  local db_state
  db_state="$(docker inspect --format '{{.State.Health.Status}}' yance-prod-db-1 2>/dev/null || echo absent)"
  [[ "${db_state}" == "healthy" ]] || die "yance-prod-db-1 is ${db_state}; refusing to start the collector against an unhealthy database"
  mkdir -p "${APP_DIR}/policy_raw"
  dc up -d collector
  echo "collector started; watch it with: $0 status"
}

cmd_stop() {
  need_env
  # `stop` (not `down`) keeps the container definition and the volume; SIGTERM gets
  # the 120s grace period so the current page is finished and its cursor committed.
  dc stop --timeout 120 collector
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_pause() {
  need_env
  need_image
  local reason="${1:-operator pause}"
  # The flag file is read on every cycle, so this takes effect without touching the
  # process, the container or the env file.  Collected documents stay readable.
  in_volume 'printf "%s\n" "$1" > /data/PAUSED; echo "paused: $(cat /data/PAUSED)"' _ "${reason}"
}

cmd_resume() {
  need_env
  need_image
  in_volume 'rm -f /data/PAUSED; echo "pause flag removed"'
}

cmd_trial() {
  local target="${1:-100}"
  [[ "${target}" =~ ^[0-9]+$ ]] || die "trial needs a document count, e.g. 'trial 100'"
  need_env
  need_image
  # Bounded by documents AND by wall clock: the number is a target, not a promise.
  in_collector scripts/policy_collection/cli.py backfill-run \
    --enable-collection \
    --max-sources 12 \
    --pages 2 \
    --docs "$(( target / 6 > 4 ? target / 6 : 4 ))" \
    --seconds 1800
  echo
  echo "verify retrieval before scaling up (token is the app's normal bearer token):"
  echo "  curl -s 'http://127.0.0.1:8000/api/v1/policies/evidence-search?q=研发费用加计扣除&limit=3' \\"
  echo "    -H \"Authorization: Bearer \$(sudo grep -m1 '^BOOTSTRAP_TOKEN=' ${APP_DIR}/.env.prod | cut -d= -f2-)\""
  echo "  (that token only works while no tenant key has been issued; otherwise use your own API key)"
}

cmd_retry() {
  local source="${1:?usage: retry <source_id>}"
  need_env
  need_image
  in_collector scripts/policy_collection/cli.py retry "${source}" --max-items 10 --trigger manual
}

cmd_reset() {
  local source="${1:?usage: reset <source_id> [--page N]}"
  shift || true
  need_env
  need_image
  in_collector scripts/policy_collection/cli.py backfill-reset "${source}" "$@"
}

cmd_alerts() {
  need_env
  need_image
  in_collector scripts/policy_collection/cli.py alerts
}

cmd_logs() {
  need_env
  dc logs --tail "${1:-200}" collector
}

cmd_backup() {
  need_env
  need_image
  local out="${1:-/var/backups/yance}"
  mkdir -p "${out}" || die "cannot create ${out} (try sudo)"
  out="$(cd "${out}" && pwd)"
  local stamp
  stamp="$(date +%Y%m%d_%H%M%S)"
  echo "== postgres dump =="
  # Credentials are read from inside the db container's own environment, so this
  # script never needs (and never prints) the production password.
  docker compose -f "${PROD_COMPOSE}" exec -T db \
    sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
    > "${out}/yance_prod_${stamp}.dump"
  [[ -s "${out}/yance_prod_${stamp}.dump" ]] || die "pg_dump produced an empty file"
  echo "wrote ${out}/yance_prod_${stamp}.dump ($(du -h "${out}/yance_prod_${stamp}.dump" | cut -f1))"
  echo
  echo "== raw evidence =="
  # The volume is the durable copy of every downloaded original.  A dump of the
  # database alone would leave citations pointing at nothing.
  docker run --rm --user "$(id -u):$(id -g)" \
    -v "${RAW_VOLUME}":/data:ro \
    -v "${out}":/backup \
    --entrypoint tar "${COLLECTOR_IMAGE}" \
    czf "/backup/policy_raw_${stamp}.tar.gz" -C /data .
  echo "wrote ${out}/policy_raw_${stamp}.tar.gz"
  echo
  echo "restore is documented in docs/policy-collection-production-runbook.md"
}

cmd_migrate_status() {
  need_env
  need_image
  # Read-only by construction: `alembic current` never writes.
  docker run --rm --network "${APP_NETWORK}" --env-file "${ENV_FILE}" \
    --entrypoint alembic "${COLLECTOR_IMAGE}" current
  echo
  echo "head expected by this release:"
  docker run --rm --network "${APP_NETWORK}" --env-file "${ENV_FILE}" \
    --entrypoint alembic "${COLLECTOR_IMAGE}" heads
}

cmd_migrate() {
  local confirm="${1:-}"
  [[ "${confirm}" == "--yes" ]] || die "this migrates the PRODUCTION schema; re-run as: $0 migrate --yes"
  need_env
  need_image
  echo "1/3 taking a database dump first"
  cmd_backup "${2:-/var/backups/yance}"
  echo "2/3 applying additive migrations (0034 -> head)"
  docker run --rm --network "${APP_NETWORK}" --env-file "${ENV_FILE}" \
    --entrypoint alembic "${COLLECTOR_IMAGE}" upgrade head
  echo "3/3 verifying"
  cmd_migrate_status
  echo "note: the running api container was NOT restarted; new columns are additive."
}

cmd_rollback() {
  local image="${1:?usage: rollback <collector-image:tag>}"
  need_env
  docker image inspect "${image}" >/dev/null 2>&1 || die "image ${image} not found locally"
  echo "1/2 stopping the current collector (in-flight document is allowed to finish)"
  dc stop --timeout 120 collector || true
  echo "2/2 re-pinning to ${image} and starting"
  # Only the collector changes.  The api image, the database and the schema are left
  # exactly as they are: pulling the collector back does not un-apply migrations,
  # because every migration this release adds is additive.
  COLLECTOR_IMAGE="${image}" docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d collector
  echo "done. The previous image is still on disk; roll forward by repeating with ${COLLECTOR_IMAGE}."
}

case "${1:-}" in
  status)         shift; cmd_status "$@" ;;
  progress)       shift; cmd_progress "$@" ;;
  start)          shift; cmd_start "$@" ;;
  stop)           shift; cmd_stop "$@" ;;
  restart)        shift; cmd_restart "$@" ;;
  pause)          shift; cmd_pause "$@" ;;
  resume)         shift; cmd_resume "$@" ;;
  trial)          shift; cmd_trial "$@" ;;
  retry)          shift; cmd_retry "$@" ;;
  reset)          shift; cmd_reset "$@" ;;
  alerts)         shift; cmd_alerts "$@" ;;
  logs)           shift; cmd_logs "$@" ;;
  backup)         shift; cmd_backup "$@" ;;
  migrate-status) shift; cmd_migrate_status "$@" ;;
  migrate)        shift; cmd_migrate "$@" ;;
  rollback)       shift; cmd_rollback "$@" ;;
  *)
    sed -n '2,40p' "${BASH_SOURCE[0]}"
    exit 1
    ;;
esac
