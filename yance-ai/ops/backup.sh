#!/usr/bin/env bash
# Yance daily database backup: pg_dump custom format + off-box copy + retention.
# Run via cron on the app server.
#
# Off-box copy (ACC-05): set YANCE_BACKUP_OFFSITE_URI to an ossutil URI
# (oss://bucket/prefix) or an rclone remote (remote:path). The script fails
# before dumping when it is unset, unless YANCE_BACKUP_OFFSITE_DISABLED=true is
# set explicitly — a local-only dump does not survive loss of the host.
set -euo pipefail
umask 077

CONTAINER="${YANCE_DB_CONTAINER:-yance-prod-db-1}"
DB_USER="${POSTGRES_USER:-yance}"
DB_NAME="${POSTGRES_DB:-yance_prod}"
BACKUP_DIR="${YANCE_BACKUP_DIR:-/opt/yance-backups}"
RETENTION_DAYS="${YANCE_BACKUP_RETENTION_DAYS:-14}"
OFFSITE_URI="${YANCE_BACKUP_OFFSITE_URI:-}"

if [[ -z "$OFFSITE_URI" ]]; then
  if [[ "${YANCE_BACKUP_OFFSITE_DISABLED:-false}" == "true" ]]; then
    echo "WARNING: off-box copy disabled explicitly; this backup is lost with the host" >&2
  else
    echo "error: YANCE_BACKUP_OFFSITE_URI is not set (set YANCE_BACKUP_OFFSITE_DISABLED=true to accept local-only backups)" >&2
    exit 2
  fi
fi

offsite_put() {  # <local file> <remote name>
  case "$OFFSITE_URI" in
    oss://*) ossutil cp -f "$1" "${OFFSITE_URI%/}/$2" >/dev/null ;;
    *)       rclone copyto "$1" "${OFFSITE_URI%/}/$2" ;;
  esac
}

offsite_cat() {  # <remote name>
  case "$OFFSITE_URI" in
    oss://*) ossutil cat "${OFFSITE_URI%/}/$1" ;;
    *)       rclone cat "${OFFSITE_URI%/}/$1" ;;
  esac
}

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/yance_${STAMP}.dump"

# Row counts per table, read just before the dump. pg_dump uses its own
# snapshot, so rows written in between can make these differ slightly; the
# restore drill reports such drift instead of treating it as corruption.
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -AtF $'\t' -c \
  "select table_name, (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from public.%I', table_name), false, true, '')))[1]::text
     from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE' order by 1" \
  > "${OUT}.counts"

# -Fc = custom format (compressed, parallel-restore friendly)
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$OUT"

# integrity check: a valid dump is listed by pg_restore
docker exec -i "$CONTAINER" pg_restore --list < "$OUT" > /dev/null

gzip "$OUT"
( cd "$BACKUP_DIR" && sha256sum "$(basename "${OUT}.gz")" > "$(basename "${OUT}.gz").sha256" )
echo "backup ok: ${OUT}.gz ($(du -h "${OUT}.gz" | cut -f1))"

if [[ -n "$OFFSITE_URI" ]]; then
  for file in "${OUT}.gz" "${OUT}.gz.sha256" "${OUT}.counts"; do
    offsite_put "$file" "$(basename "$file")"
  done
  expected="$(cut -d' ' -f1 "${OUT}.gz.sha256")"
  remote="$(offsite_cat "$(basename "${OUT}.gz")" | sha256sum | cut -d' ' -f1)"
  if [[ "$remote" != "$expected" ]]; then
    echo "error: off-box copy checksum mismatch for $(basename "${OUT}.gz")" >&2
    exit 3
  fi
  echo "offsite ok: ${OFFSITE_URI%/}/$(basename "${OUT}.gz") (sha256 verified by read-back)"
fi

# retention: prune dumps older than RETENTION_DAYS (our prefix only)
if [[ "${YANCE_BACKUP_PRUNE_ENABLED:-false}" == "true" ]]; then
  # Enable only after an operator verifies off-box copies and restore evidence.
  find "$BACKUP_DIR" -maxdepth 1 -name 'yance_*.dump.gz' -type f -mtime "+$RETENTION_DAYS" -delete
  echo "retention: kept last ${RETENTION_DAYS} days (explicit opt-in)"
else
  echo "retention: pruning disabled; verify off-box recovery before enabling"
fi
