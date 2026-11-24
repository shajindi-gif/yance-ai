#!/usr/bin/env bash
# Restore drill (ACC-05): restore the newest backup into a throwaway database,
# verify checksum, Alembic revision and per-table row counts, and print timings.
#
# Never point this at the production database. The target name must start with
# yance_restore_ and must not exist yet; it is created here and kept for
# inspection (drop it afterwards under the approved retention process).
#
# Required: YANCE_RESTORE_HOST, YANCE_RESTORE_PORT, YANCE_RESTORE_USER
#           (password via ~/.pgpass or PGPASSWORD set by the operator)
# Optional: YANCE_BACKUP_DIR (default /opt/yance-backups), BACKUP_FILE (default newest),
#           YANCE_RESTORE_DB (default yance_restore_<timestamp>)
set -euo pipefail

BACKUP_DIR="${YANCE_BACKUP_DIR:-/opt/yance-backups}"
BACKUP_FILE="${BACKUP_FILE:-$(ls -1t "$BACKUP_DIR"/yance_*.dump.gz 2>/dev/null | head -1)}"
TARGET_DB="${YANCE_RESTORE_DB:-yance_restore_$(date +%Y%m%d_%H%M%S)}"
: "${YANCE_RESTORE_HOST:?set YANCE_RESTORE_HOST}" "${YANCE_RESTORE_PORT:?set YANCE_RESTORE_PORT}" "${YANCE_RESTORE_USER:?set YANCE_RESTORE_USER}"
PG=(--host "$YANCE_RESTORE_HOST" --port "$YANCE_RESTORE_PORT" --username "$YANCE_RESTORE_USER")

[[ -n "$BACKUP_FILE" && -f "$BACKUP_FILE" ]] || { echo "error: no backup found in $BACKUP_DIR" >&2; exit 2; }
[[ "$TARGET_DB" == yance_restore_* ]] || { echo "error: target database must be named yance_restore_*" >&2; exit 2; }

start=$(date +%s)
echo "backup:  $BACKUP_FILE"
( cd "$(dirname "$BACKUP_FILE")" && sha256sum -c "$(basename "$BACKUP_FILE").sha256" >/dev/null ) \
  || { echo "error: checksum mismatch" >&2; exit 3; }
echo "sha256:  ok"

# Decompress to a file first: pg_restore can stop reading a stream before EOF,
# which makes gunzip die of SIGPIPE under pipefail.
dump_file="$(mktemp "${TMPDIR:-/tmp}/yance_restore_XXXXXX.dump")"
trap 'rm -f "$dump_file"' EXIT
gunzip -c "$BACKUP_FILE" > "$dump_file"
createdb "${PG[@]}" "$TARGET_DB"
pg_restore "${PG[@]}" --dbname "$TARGET_DB" --no-owner --exit-on-error --jobs "${YANCE_RESTORE_JOBS:-2}" "$dump_file"
restored=$(date +%s)

revision="$(psql "${PG[@]}" -d "$TARGET_DB" -Atc "select string_agg(version_num, ',') from alembic_version")"
echo "alembic: $revision"
[[ -n "$revision" && "$revision" != *,* ]] || { echo "error: expected exactly one Alembic revision" >&2; exit 4; }

counts_file="${BACKUP_FILE%.gz}.counts"
mismatch=0
if [[ -f "$counts_file" ]]; then
  while IFS=$'\t' read -r table expected; do
    actual="$(psql "${PG[@]}" -d "$TARGET_DB" -Atc "select count(*) from public.\"$table\"" 2>/dev/null || echo missing)"
    if [[ "$actual" != "$expected" ]]; then
      echo "drift:   $table expected=$expected restored=$actual"
      [[ "$actual" == missing ]] && mismatch=1
    fi
  done < "$counts_file"
  echo "tables:  $(wc -l < "$counts_file") compared"
else
  echo "warning: no row-count manifest next to the backup (made by an older backup.sh)"
fi

end=$(date +%s)
echo "restore: $((restored - start))s, total drill: $((end - start))s, target: $TARGET_DB"
if (( mismatch )); then
  echo "error: tables missing after restore" >&2
  exit 5
fi
echo "drill ok"
