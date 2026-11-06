#!/usr/bin/env bash
# One entry point for collector operations on the server.
#
# Everything here is a thin, honest wrapper over the CLI that already exists
# (`scripts/policy_collection/cli.py` and `python -m app.workers.policy_collector`).
# It exists so that an on-call engineer under pressure does not have to remember
# five different argument shapes — and so that the risky commands are spelled out
# rather than improvised.
#
# Usage:
#   ./ops/collector.sh status              # health, backlog, recent runs
#   ./ops/collector.sh progress            # backfill cursors + searchable counts
#   ./ops/collector.sh start               # start the collector container
#   ./ops/collector.sh stop                # stop it (in-flight document finishes)
#   ./ops/collector.sh pause               # keep it running, download nothing
#   ./ops/collector.sh resume              # lift the pause
#   ./ops/collector.sh trial 100           # bounded trial batch of ~N documents
#   ./ops/collector.sh retry <source_id>   # re-read one source
#   ./ops/collector.sh reset <source_id>   # clear a parked/stuck cursor
#   ./ops/collector.sh alerts              # persistent failures + page gaps
#   ./ops/collector.sh backup [dir]        # pg_dump + raw evidence tarball
#   ./ops/collector.sh rollback <ref>      # stop collector, checkout ref, migrate down
#
# Requires: docker compose v2 on the host, .env.prod present next to this repo.

set -euo pipefail

# ops/ lives inside the application checkout (yance-ai/), which is itself inside the
# git root (yance/).  Both are needed: compose files next to the app, git commands
# at the repo root.
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${APP_DIR}/.." && pwd)"
COMPOSE_FILE="${APP_DIR}/docker-compose.collector.yml"
PROD_COMPOSE="${APP_DIR}/docker-compose.prod.yml"
ENV_FILE="${APP_DIR}/.env.prod"
PY="${APP_DIR}/.venv/bin/python"
CLI="${APP_DIR}/scripts/policy_collection/cli.py"

die() { echo "error: $*" >&2; exit 1; }

need_cli() { [[ -x "${PY}" ]] || die "python venv missing at ${PY}"; }

cmd_status() {
  echo "== collector process =="
  docker compose -f "${COMPOSE_FILE}" ps || true
  echo
  echo "== scheduling health =="
  need_cli
  ( cd "${APP_DIR}" && "${PY}" -m app.workers.policy_collector --status ) || true
  echo
  echo "== backlog / runs =="
  ( cd "${APP_DIR}" && "${PY}" "${CLI}" status ) || true
}

cmd_progress() {
  need_cli
  cd "${APP_DIR}"
  "${PY}" "${CLI}" backfill-status
  echo
  "${PY}" "${CLI}" backlog
  echo
  "${PY}" - <<'PY'
from app.core.db import SessionLocal
from app.services.policy_collection.keyword_search import searchable_counts

db = SessionLocal()
try:
    print("searchable corpus:", searchable_counts(db))
finally:
    db.close()
PY
}

cmd_start() {
  docker compose -f "${PROD_COMPOSE}" --env-file "${ENV_FILE}" up -d db migrate api
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d collector
  echo "collector started; watch it with: $0 status"
}

cmd_stop() {
  # `down` sends SIGTERM and waits the 120s grace period, so the current page is
  # finished and its cursor committed instead of being abandoned mid-write.
  docker compose -f "${COMPOSE_FILE}" down
}

cmd_pause() {
  need_cli
  cd "${APP_DIR}"
  # The flag file is read on every cycle, so this takes effect without touching
  # the process, the container or the env file.  Collected documents stay readable.
  "${PY}" "${CLI}" pause --global --reason "${2:-operator pause}"
}

cmd_resume() {
  need_cli
  cd "${APP_DIR}"
  "${PY}" "${CLI}" resume --global
}

cmd_trial() {
  local target="${1:-100}"
  [[ "${target}" =~ ^[0-9]+$ ]] || die "trial needs a document count, e.g. 'trial 100'"
  need_cli
  cd "${APP_DIR}"
  # Bounded by documents AND by wall clock: the number is a target, not a promise.
  "${PY}" "${CLI}" backfill-run \
    --enable-collection \
    --max-sources 12 \
    --pages 2 \
    --docs "$(( target / 6 > 4 ? target / 6 : 4 ))" \
    --seconds 1800
  echo
  echo "verify retrieval before scaling up:"
  echo "  curl -s 'http://127.0.0.1:8000/api/v1/policies/evidence-search?q=研发费用加计扣除&limit=3' -H \"Authorization: Bearer <token>\""
}

cmd_retry() {
  local source="${1:?usage: retry <source_id>}"
  need_cli
  cd "${APP_DIR}"
  "${PY}" "${CLI}" retry "${source}" --max-items 10 --trigger manual
}

cmd_reset() {
  local source="${1:?usage: reset <source_id> [--page N]}"
  shift || true
  need_cli
  cd "${APP_DIR}"
  "${PY}" "${CLI}" backfill-reset "${source}" "$@"
}

cmd_alerts() {
  need_cli
  cd "${APP_DIR}"
  "${PY}" "${CLI}" alerts
}

cmd_backup() {
  local out="${1:-/var/backups/yance}"
  mkdir -p "${out}"
  local stamp
  stamp="$(date +%Y%m%d_%H%M%S)"
  echo "== postgres dump =="
  docker compose -f "${PROD_COMPOSE}" exec -T db \
    pg_dump -U yance -d yance_prod --format=custom \
    > "${out}/yance_prod_${stamp}.dump"
  echo "wrote ${out}/yance_prod_${stamp}.dump"
  echo
  echo "== raw evidence =="
  # The volume is the durable copy of every downloaded original.  A dump of the
  # database alone would leave citations pointing at nothing.
  docker run --rm \
    -v yance_policy_raw_prod:/data:ro \
    -v "${out}":/backup \
    alpine tar czf "/backup/policy_raw_${stamp}.tar.gz" -C /data .
  echo "wrote ${out}/policy_raw_${stamp}.tar.gz"
  echo
  echo "restore is documented in docs/policy-collection-production-runbook.md"
}

cmd_rollback() {
  local ref="${1:?usage: rollback <git-ref>}"
  echo "1/3 stopping collector (in-flight document is allowed to finish)"
  docker compose -f "${COMPOSE_FILE}" down
  echo "2/3 checking out ${ref}"
  ( cd "${REPO_ROOT}" && git checkout "${ref}" )
  echo "3/3 app stack back up (migrations are additive; run downgrade only if the"
  echo "    release notes for ${ref} say the schema is incompatible)"
  docker compose -f "${PROD_COMPOSE}" --env-file "${ENV_FILE}" up -d db migrate api
  echo "done. Re-start the collector with: $0 start"
}

case "${1:-}" in
  status)   shift; cmd_status "$@" ;;
  progress) shift; cmd_progress "$@" ;;
  start)    shift; cmd_start "$@" ;;
  stop)     shift; cmd_stop "$@" ;;
  pause)    shift; cmd_pause "$@" ;;
  resume)   shift; cmd_resume "$@" ;;
  trial)    shift; cmd_trial "$@" ;;
  retry)    shift; cmd_retry "$@" ;;
  reset)    shift; cmd_reset "$@" ;;
  alerts)   shift; cmd_alerts "$@" ;;
  backup)   shift; cmd_backup "$@" ;;
  rollback) shift; cmd_rollback "$@" ;;
  *)
    sed -n '2,30p' "${BASH_SOURCE[0]}"
    exit 1
    ;;
esac
