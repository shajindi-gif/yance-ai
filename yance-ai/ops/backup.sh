#!/usr/bin/env bash
# Yance daily database backup: pg_dump custom format + retention.
# Run via cron on the app server. Never keep backups only on the same disk as
# the database — copy the output off-box (rclone / scp / object storage) as a
# separate step; this script produces local dumps and prunes old ones.
set -euo pipefail

CONTAINER="${YANCE_DB_CONTAINER:-yance-prod-db-1}"
DB_USER="${POSTGRES_USER:-yance}"
DB_NAME="${POSTGRES_DB:-yance_prod}"
BACKUP_DIR="${YANCE_BACKUP_DIR:-/opt/yance-backups}"
RETENTION_DAYS="${YANCE_BACKUP_RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/yance_${STAMP}.dump"

# -Fc = custom format (compressed, parallel-restore friendly)
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$OUT"

# integrity check: a valid dump is listed by pg_restore
docker exec -i "$CONTAINER" pg_restore --list < "$OUT" > /dev/null

gzip "$OUT"
echo "backup ok: ${OUT}.gz ($(du -h "${OUT}.gz" | cut -f1))"

# retention: prune dumps older than RETENTION_DAYS (our prefix only)
find "$BACKUP_DIR" -maxdepth 1 -name 'yance_*.dump.gz' -type f -mtime "+$RETENTION_DAYS" -delete
echo "retention: kept last ${RETENTION_DAYS} days"
