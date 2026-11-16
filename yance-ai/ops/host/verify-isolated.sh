#!/usr/bin/env bash
# verify-isolated.sh — rehearse the production upgrade on a throwaway database.
#
# What it proves, in order:
#   1. the preflight dump restores into an empty PG16 database, still at 0034;
#   2. 0034 -> head migrates cleanly, every pre-existing row survives untouched,
#      and the new policy_* tables plus the pg_trgm indexes appear;
#   3. a real collection run writes documents and chunks into that database;
#   4. a normal account (password login, no shortcuts) can retrieve the newly
#      collected text through GET /api/v1/policies/evidence-search.
#
# Isolation rules:
#   * one throwaway container, loopback port only, no volume, --rm on exit;
#   * the production database container is only *inspected*, never connected to;
#   * the API started here listens on 127.0.0.1:18080 with the isolated DATABASE_URL;
#   * every artefact lands under a temp dir and is removed unless --keep is given.
#
# Docker is used here only as a disposable Postgres. The collector itself runs as a
# plain host process; step 3 invokes it exactly the way the systemd unit does.

set -Eeuo pipefail

HOME_DIR="${COLLECTOR_HOME:-/opt/yance/collector-20261106-r3}"
VENV_PY="${HOME_DIR}/.venv/bin/python"
CLI="${HOME_DIR}/scripts/policy_collection/cli.py"
BACKUP_DIR="/opt/yance/backups/collector-preflight-20261106T120545Z"
PG_IMAGE="pgvector/pgvector:pg16"
PG_CONTAINER="yance-verify-pg"
PG_PORT="55433"
API_PORT="18080"
DB_NAME="yance_verify"
KEEP=0
SKIP_COLLECT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    --skip-collect) SKIP_COLLECT=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

WORK="$(mktemp -d /var/tmp/yance-verify.XXXXXX)"
RAW_DIR="${WORK}/policy_raw"
LOG="${WORK}/verify.log"
RESULTS="${WORK}/results.tsv"
: >"${RESULTS}"

say()  { printf '\n\033[1m== %s ==\033[0m\n' "$*" | tee -a "${LOG}"; }
info() { printf '   %s\n' "$*" | tee -a "${LOG}"; }
pass() { printf 'PASS\t%s\t%s\n' "$1" "$2" >>"${RESULTS}"; printf '   \033[32mPASS\033[0m %s — %s\n' "$1" "$2" | tee -a "${LOG}"; }
fail() { printf 'FAIL\t%s\t%s\n' "$1" "$2" >>"${RESULTS}"; printf '   \033[31mFAIL\033[0m %s — %s\n' "$1" "$2" | tee -a "${LOG}"; }

# $1 = SQL, $2 = database (defaults to the verify database, which does not exist yet
# during section 1 — that is why the version probe below passes "postgres" explicitly).
# Retries: the official image runs initdb and then restarts the postmaster, so a single
# successful exec can be followed by a socket that is momentarily gone again.
psql_v() {
  local sql="$1" db="${2:-${DB_NAME}}" out i
  for i in $(seq 1 10); do
    if out="$(docker exec -e PGPASSWORD=verify "${PG_CONTAINER}" psql -U postgres -d "${db}" -tAc "${sql}" 2>/dev/null)"; then
      printf '%s\n' "${out}"
      return 0
    fi
    sleep 2
  done
  docker exec -e PGPASSWORD=verify "${PG_CONTAINER}" psql -U postgres -d "${db}" -tAc "${sql}"
}

cleanup() {
  local code=$?
  set +e
  if [[ -n "${API_PID:-}" ]]; then kill "${API_PID}" 2>/dev/null; wait "${API_PID}" 2>/dev/null; fi
  docker rm -f "${PG_CONTAINER}" >/dev/null 2>&1
  if [[ ${KEEP} -eq 1 ]]; then
    echo "artefacts kept in ${WORK}"
  else
    rm -rf "${WORK}"
  fi
  exit "${code}"
}
trap cleanup EXIT

command -v docker >/dev/null || { echo "docker CLI required for the disposable Postgres" >&2; exit 2; }
[[ -x "${VENV_PY}" ]] || { echo "missing venv python ${VENV_PY}" >&2; exit 2; }
[[ -f "${BACKUP_DIR}/database.dump" ]] || { echo "missing ${BACKUP_DIR}/database.dump" >&2; exit 2; }
info "backup     : ${BACKUP_DIR}"
info "work dir   : ${WORK}"
info "venv       : ${VENV_PY}"

# ----------------------------------------------------------------------------- 0
say '0. preflight'
docker rm -f "${PG_CONTAINER}" >/dev/null 2>&1 || true
PROD_PID="$(docker inspect -f '{{.State.Pid}}' yance-prod-db-1 2>/dev/null || echo none)"
info "production db container pid: ${PROD_PID} (never touched below)"
pass preflight "backup present, venv present, prod db pid=${PROD_PID}"

# ----------------------------------------------------------------------------- 1
say "1. throwaway postgres on 127.0.0.1:${PG_PORT} (no volume, --rm)"
docker run -d --rm --name "${PG_CONTAINER}" \
  -e POSTGRES_PASSWORD=verify -e POSTGRES_DB=postgres \
  -p "127.0.0.1:${PG_PORT}:5432" "${PG_IMAGE}" >/dev/null
# First boot of this image runs initdb (8-12s), so poll the container state as well
# as pg_isready: a container that died must be reported, not waited on for 60s.
ready=0
streak=0
for _ in $(seq 1 90); do
  # A real query, not pg_isready: during initdb the postmaster briefly accepts then
  # restarts, and pg_isready can report ready while a query would still fail.
  if docker exec -e PGPASSWORD=verify "${PG_CONTAINER}" psql -U postgres -d postgres -tAc 'select 1' >/dev/null 2>&1; then
    # Require three consecutive successes: initdb hands over to the real postmaster
    # a few seconds after the first answer, and that restart briefly kills the socket.
    streak=$((streak + 1))
    if [[ "${streak}" -ge 3 ]]; then ready=1; break; fi
    sleep 2
    continue
  fi
  streak=0
  if [[ "$(docker inspect -f '{{.State.Running}}' "${PG_CONTAINER}" 2>/dev/null || echo false)" != "true" ]]; then
    info "container exited during startup"
    docker logs "${PG_CONTAINER}" 2>&1 | tail -20 | tee -a "${LOG}"
    break
  fi
  sleep 1
done
if [[ "${ready}" -ne 1 ]]; then
  fail startup 'postgres did not become ready'
  docker logs "${PG_CONTAINER}" 2>&1 | tail -20 | tee -a "${LOG}"
  exit 1
fi
PSQL_VER="$(psql_v 'select version()' postgres)"
info "${PSQL_VER:0:80}"
pass postgres-up "throwaway instance ready on loopback"

# ----------------------------------------------------------------------------- 2
say '2. restore the preflight dump into an empty database'
docker exec "${PG_CONTAINER}" createdb -U postgres "${DB_NAME}"
docker exec -i "${PG_CONTAINER}" pg_restore -U postgres -d "${DB_NAME}" \
  --no-owner --no-privileges --single-transaction <"${BACKUP_DIR}/database.dump" 2>"${WORK}/restore.err" \
  && pass restore 'pg_restore completed' \
  || { fail restore 'pg_restore failed'; sed -n '1,15p' "${WORK}/restore.err" | tee -a "${LOG}"; }

REV_BEFORE="$(psql_v "select version_num from alembic_version")"
info "alembic before : ${REV_BEFORE}"
[[ "${REV_BEFORE}" == "20261029_0034" ]] && pass baseline-rev 'database restored at 0034' \
  || fail baseline-rev "expected 20261029_0034, got ${REV_BEFORE}"

TABLES_BEFORE="$(psql_v "select count(*) from information_schema.tables where table_schema='public'")"
ROWS_BEFORE="$(psql_v "select string_agg(n||':'||c, '|' order by n) from (select relname n, n_live_tup c from pg_stat_user_tables) s")"
info "public tables  : ${TABLES_BEFORE}"

# ----------------------------------------------------------------------------- 3
say '3. migrate 0034 -> head on the isolated database'
ISO_URL="postgresql+psycopg://postgres:verify@127.0.0.1:${PG_PORT}/${DB_NAME}"
(
  cd "${HOME_DIR}"
  DATABASE_URL="${ISO_URL}" APP_ENV=staging \
    "${VENV_PY}" -m alembic upgrade head
) >"${WORK}/alembic.log" 2>&1 && pass migrate 'alembic upgrade head succeeded' \
  || { fail migrate 'alembic upgrade head failed'; tail -30 "${WORK}/alembic.log" | tee -a "${LOG}"; }
tail -4 "${WORK}/alembic.log" | tee -a "${LOG}"

REV_AFTER="$(psql_v "select version_num from alembic_version")"
info "alembic after  : ${REV_AFTER}"
[[ "${REV_AFTER}" == "20261106_0038" ]] && pass head-rev 'at 20261106_0038' || fail head-rev "unexpected ${REV_AFTER}"

TABLES_AFTER="$(psql_v "select count(*) from information_schema.tables where table_schema='public'")"
info "public tables  : ${TABLES_AFTER} (was ${TABLES_BEFORE})"
[[ "${TABLES_AFTER}" -gt "${TABLES_BEFORE}" ]] && pass new-tables "added $((TABLES_AFTER - TABLES_BEFORE)) tables" \
  || fail new-tables 'no new tables appeared'

MISSING="$(psql_v "select string_agg(t, ',') from unnest(array['policy_sources','policy_collection_runs','policy_raw_evidence','policy_attachments','policy_document_keys','policy_origins','policy_application_windows','parks']) t where not exists (select 1 from information_schema.tables where table_schema='public' and table_name=t)")"
[[ -z "${MISSING}" ]] && pass new-tables-named 'all expected policy_*/parks tables exist' \
  || fail new-tables-named "missing: ${MISSING}"

IDX="$(psql_v "select string_agg(indexname, ',') from pg_indexes where indexname in ('ix_policies_title_trgm','ix_policy_chunks_content_trgm','ix_policy_versions_title_trgm')")"
[[ "$(grep -o ',' <<<"${IDX}" | wc -l)" -eq 2 ]] && pass trgm-indexes '3 pg_trgm indexes present' \
  || fail trgm-indexes "found: ${IDX:-none}"

EXT="$(psql_v "select string_agg(extname||' '||extversion, ',') from pg_extension")"
info "extensions     : ${EXT}"
grep -q 'vector' <<<"${EXT}" && grep -q 'pg_trgm' <<<"${EXT}" \
  && pass extensions 'vector + pg_trgm present' || fail extensions "${EXT}"

# ----------------------------------------------------------------------------- 4
say '4. row-level comparison of the pre-existing tables'
ROWS_AFTER="$(psql_v "select string_agg(n||':'||c, '|' order by n) from (select relname n, n_live_tup c from pg_stat_user_tables) s")"
python3 - "${ROWS_BEFORE}" "${ROWS_AFTER}" <<'PY' | tee -a "${LOG}"
import sys
before = dict(kv.split(':', 1) for kv in sys.argv[1].split('|') if kv)
after = dict(kv.split(':', 1) for kv in sys.argv[2].split('|') if kv)
changed = {k: (before[k], after.get(k)) for k in before if before[k] != after.get(k)}
if changed:
    print(f"   changed tables: {changed}")
    raise SystemExit(1)
print(f"   {len(before)} pre-existing tables unchanged")
PY
[[ ${PIPESTATUS[0]} -eq 0 ]] && pass rows-intact 'every pre-existing table kept its row count' \
  || fail rows-intact 'row counts changed'

# ----------------------------------------------------------------------------- 5
if [[ ${SKIP_COLLECT} -eq 1 ]]; then
  say '5. collection rehearsal skipped (--skip-collect)'
else
  say '5. real collection run against the isolated database'
  install -d -m 0750 "${RAW_DIR}"
  (
    cd "${HOME_DIR}"
    DATABASE_URL="${ISO_URL}" APP_ENV=staging \
    POLICY_COLLECTION_ENABLED=true \
    POLICY_COLLECTION_RAW_DIR="${RAW_DIR}" \
    POLICY_COLLECTION_ATTACHMENT_DIR="${RAW_DIR}/attachments" \
    POLICY_COLLECTION_MIN_FREE_DISK_MB=200 \
    POLICY_COLLECTION_LLM_ENABLED=false \
    "${VENV_PY}" "${CLI}" run --level national --limit 2 --trigger isolated-verify
  ) >"${WORK}/collect.log" 2>&1 && pass collect 'collector run finished' \
    || { fail collect 'collector run failed'; tail -25 "${WORK}/collect.log" | tee -a "${LOG}"; }
  tail -12 "${WORK}/collect.log" | tee -a "${LOG}"

  P="$(psql_v 'select count(*) from policies')"
  C="$(psql_v 'select count(*) from policy_chunks')"
  E="$(psql_v 'select count(*) from policy_raw_evidence')"
  # Judge dedupe on the rows this run actually wrote. The restored backup still holds
  # legacy rows, so counting duplicates across all of `policies` would report history,
  # not the collector's behaviour.
  DUPE="$(psql_v "select count(*) from (select url_normalized from policy_raw_evidence where purpose='document' group by url_normalized having count(*)>1) s")"
  HIST_DUPE="$(psql_v 'select count(*) from (select source_url from policies group by source_url having count(*)>1) s')"
  info "policies=${P} chunks=${C} raw_evidence=${E} duplicate_evidence_urls=${DUPE} historical_duplicate_policy_urls=${HIST_DUPE}"
  [[ "${P}" -gt 0 && "${C}" -gt 0 ]] && pass collect-rows "policies=${P} chunks=${C}" || fail collect-rows 'nothing collected'
  [[ "${DUPE}" -eq 0 ]] && pass dedupe "no duplicate source_url among ${E} newly collected documents" \
  || fail dedupe "${DUPE} duplicated urls among newly collected documents"
  FILES="$(find "${RAW_DIR}" -type f ! -name 'collector_state.json' ! -name 'PAUSED' | wc -l)"
  info "raw files on disk: ${FILES} under ${RAW_DIR}"
  [[ "${FILES}" -gt 0 ]] && pass raw-files "${FILES} files persisted" || fail raw-files 'no raw evidence files'

  # ------------------------------------------------------------------------- 6
  say '6. normal-account retrieval through the API (the point of the whole exercise)'
  PROV_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
  JWT_SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
  (
    cd "${HOME_DIR}"
    DATABASE_URL="${ISO_URL}" APP_ENV=staging \
    JWT_SECRET="${JWT_SECRET}" \
    TENANT_PROVISIONING_TOKEN="${PROV_TOKEN}" \
    POLICY_COLLECTION_RAW_DIR="${RAW_DIR}" \
    "${VENV_PY}" -m uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT}" --log-level warning
  ) >"${WORK}/api.log" 2>&1 &
  API_PID=$!
  HEALTH_CODE=000
  for _ in $(seq 1 90); do
    HEALTH_CODE="$(curl -s -o "${WORK}/health.json" -w '%{http_code}' \
      "http://127.0.0.1:${API_PORT}/health" 2>/dev/null || true)"
    # curl prints 000 on connection failure and appends nothing on exit; normalise to
    # the last three characters so "000000" can never be mistaken for a live server.
    HEALTH_CODE="${HEALTH_CODE: -3}"
    [[ -z "${HEALTH_CODE}" ]] && HEALTH_CODE=000
    [[ "${HEALTH_CODE}" != "000" ]] && break
    sleep 1
  done
  info "GET /health HTTP ${HEALTH_CODE} body: $(head -c 200 "${WORK}/health.json" 2>/dev/null || true)"
  # A non-2xx /health (e.g. a degraded dependency check) still means the API process
  # is serving; only a dead socket counts as "did not start".
  [[ "${HEALTH_CODE}" != "000" ]] \
    && pass api-up "isolated API answering on 127.0.0.1:${API_PORT}" \
    || { fail api-up 'API did not start'; tail -20 "${WORK}/api.log" | tee -a "${LOG}"; }

  PW="verify-$(python3 -c 'import secrets;print(secrets.token_urlsafe(9))')"
  STAMP="$(date +%s)"
  SLUG="verify-${STAMP}"
  EMAIL="verify-${STAMP}@example.com"
  code=$(curl -s -o "${WORK}/prov.json" -w '%{http_code}' -X POST \
    "http://127.0.0.1:${API_PORT}/api/v1/auth/provision-tenant" \
    -H "Content-Type: application/json" -H "X-Tenant-Provisioning-Token: ${PROV_TOKEN}" \
    -d "{\"tenant_name\":\"Verify ${STAMP}\",\"tenant_slug\":\"${SLUG}\",\"owner_email\":\"${EMAIL}\",\"owner_name\":\"Verify Owner\",\"owner_password\":\"${PW}\"}")
  info "provision-tenant HTTP ${code}"
  [[ "${code}" == "200" || "${code}" == "201" ]] && pass tenant "tenant ${SLUG} + owner created in isolated db" \
    || { fail tenant "HTTP ${code}: $(head -c 300 "${WORK}/prov.json")"; }

  code=$(curl -s -o "${WORK}/login.json" -w '%{http_code}' -X POST \
    "http://127.0.0.1:${API_PORT}/api/v1/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "X-Tenant-Slug: ${SLUG}" \
    --data-urlencode "username=${EMAIL}" --data-urlencode "password=${PW}")
  TOKEN="$(python3 -c "import json;print(json.load(open('${WORK}/login.json')).get('access_token',''))" 2>/dev/null || echo '')"
  info "password login HTTP ${code}"
  [[ -n "${TOKEN}" ]] && pass login "normal user ${EMAIL} authenticated with email + password" \
    || fail login "HTTP ${code}: $(head -c 300 "${WORK}/login.json" 2>/dev/null || true)"

  Q="$(psql_v "select title from policies limit 1")"
  WORD="$(python3 -c "
t='''${Q}'''
print(t[:4] if len(t)>=4 else t)")"
  info "searching for: ${WORD}"
  code=$(curl -s -o "${WORK}/search.json" -w '%{http_code}' -G \
    "http://127.0.0.1:${API_PORT}/api/v1/policies/evidence-search" \
    -H "Authorization: Bearer ${TOKEN}" --data-urlencode "q=${WORD}" --data-urlencode 'limit=5')
  COUNT="$(python3 -c "
import json
try:
    d=json.load(open('${WORK}/search.json'))
    print(d.get('count', 0))
except Exception:
    print(-1)")"
  info "evidence-search HTTP ${code} count=${COUNT}"
  python3 - "${WORK}/search.json" <<'PY' | tee -a "${LOG}" || true
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    raise SystemExit(0)
print(f"   retrieval : {d.get('retrieval')}")
print(f"   corpus    : {d.get('corpus')}")
for h in d.get("hits", [])[:3]:
    print(f"   hit: {h.get('policy_title')} [{h.get('policy_status')}]")
PY
  [[ "${code}" == "200" && "${COUNT}" -ge 1 ]] \
    && pass web-retrieval "normal user retrieved ${COUNT} hit(s) — collected text is reachable from the web" \
    || fail web-retrieval "HTTP ${code} count=${COUNT} (raw files on disk do not make the corpus searchable)"
fi

# ----------------------------------------------------------------------------- 7
say '7. teardown'
kill "${API_PID}" 2>/dev/null || true; wait "${API_PID}" 2>/dev/null || true; API_PID=""
docker rm -f "${PG_CONTAINER}" >/dev/null 2>&1 || true
pass teardown 'throwaway container and API removed'

say 'summary'
column -t -s $'\t' "${RESULTS}" | tee -a "${LOG}"
FAILED="$(grep -c '^FAIL' "${RESULTS}" || true)"
echo
if [[ "${FAILED}" -eq 0 ]]; then
  echo "ALL CHECKS PASSED — 0034 -> head is safe to plan for production."
else
  echo "${FAILED} CHECK(S) FAILED — do not migrate production yet."
fi
[[ ${KEEP} -eq 1 ]] && echo "logs: ${LOG}"
exit $([[ "${FAILED}" -eq 0 ]] && echo 0 || echo 1)
