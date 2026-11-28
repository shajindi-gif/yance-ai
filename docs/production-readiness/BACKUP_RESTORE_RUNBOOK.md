# PostgreSQL Backup and Restore Runbook

Status: **logical backup/restore procedure tested locally in Phase 11; managed-production scheduling remains environment work**.

## Current recovery objectives (ACC-05, 2026-11-24)

| Objective | Current value | Why |
|---|---|---|
| RPO | **up to 24 hours** | `ops/backup.sh` takes one logical dump per day; there is no WAL archiving or point-in-time recovery |
| RTO | **not measured on production-sized data** | local drill on 724 KB of synthetic data took ~1 s and does not predict production |
| Off-box copy | **required by `ops/backup.sh`** | the script exits non-zero unless `YANCE_BACKUP_OFFSITE_URI` is set or `YANCE_BACKUP_OFFSITE_DISABLED=true` is set explicitly |

Recommended upgrade path, in order: (1) enable the off-box copy below today; (2) enable WAL archiving
(e.g. `archive_command` to object storage via wal-g/pgBackRest) or move to managed RDS with
point-in-time recovery, bringing RPO to minutes; (3) run `ops/restore_drill.sh` monthly and record RTO.

## Automated daily backup with off-box copy

```bash
# /etc/cron.d/yance-backup (operator-installed; values are examples)
YANCE_BACKUP_DIR=/opt/yance-backups
YANCE_BACKUP_OFFSITE_URI=oss://<bucket>/yance/db     # or an rclone remote such as cos:yance-db
17 3 * * * root /opt/yance/ops/backup.sh >> /var/log/yance-backup.log 2>&1
```

Each run writes `yance_<stamp>.dump.gz`, its `.sha256` and a per-table `.counts` manifest, uploads all
three, then reads the dump back from the remote and compares SHA-256. Any failure exits non-zero.
The bucket credentials belong to the host's `ossutil`/`rclone` configuration with write-only or
least-privilege access (see `ops/aliyun/oss-ram-policy.example.json`), never to this repository.

## Scripted restore drill

```bash
YANCE_RESTORE_HOST=<isolated-host> YANCE_RESTORE_PORT=5432 YANCE_RESTORE_USER=<restore-user> \
  /opt/yance/ops/restore_drill.sh
```

The script verifies the checksum, restores into a new `yance_restore_*` database (it refuses any other
name), checks for exactly one Alembic revision and compares per-table row counts with the manifest.
Counts are read just before `pg_dump` takes its own snapshot, so small drift on busy tables is reported
as `drift:` lines; a missing table fails the drill. Record the printed timings as the measured RTO.

## Preconditions

- Use PostgreSQL client tools compatible with the server major version.
- The operator needs scoped read access to the source and ownership of an isolated restore target.
- Store credentials in the approved secret manager or process environment; never in shell history, repository files or backup names.
- Store encrypted backups outside the primary database failure domain with retention and access logging.

## Backup

Use an explicit source database and destination file. Do not use a broad home or repository directory.

```bash
pg_dump \
  --host "$YANCE_PG_HOST" \
  --port "$YANCE_PG_PORT" \
  --username "$YANCE_PG_USER" \
  --dbname "$YANCE_PG_DATABASE" \
  --format custom \
  --file "/var/backups/yance/yance-YYYYMMDDTHHMMSSZ.dump"
```

Generate and store a SHA-256 checksum, database/server version, Alembic revision, start/end timestamps and operator/run identifier next to the encrypted backup.

## Restore drill

The restore target must be a newly created, explicitly named isolated database. Never point this procedure at production.

```bash
createdb \
  --host "$YANCE_RESTORE_HOST" \
  --port "$YANCE_RESTORE_PORT" \
  --username "$YANCE_RESTORE_USER" \
  yance_restore_YYYYMMDD

pg_restore \
  --host "$YANCE_RESTORE_HOST" \
  --port "$YANCE_RESTORE_PORT" \
  --username "$YANCE_RESTORE_USER" \
  --dbname yance_restore_YYYYMMDD \
  --exit-on-error \
  "/var/backups/yance/yance-YYYYMMDDTHHMMSSZ.dump"
```

## Verification

1. Verify the checksum before restore.
2. Confirm exactly one Alembic revision and that it equals the expected release revision.
3. Compare source/restore row counts for tenants, users, companies, documents, policies, agent runs, applications, artifacts, usage, payment provider events and audit logs.
4. Run `/health/ready` against an application configured only for the restore target.
5. Run a read-only authenticated tenant-isolation smoke and retrieve one known artifact checksum.
6. Record elapsed time, data timestamp and any warnings. Delete the isolated target only under the approved retention process.

## Cadence and escalation

- Daily automated backup and at least monthly restore drill are release-candidate targets.
- A failed backup or checksum is SEV-2.
- RPO/RTO remain provisional until two consecutive managed-environment drills meet target.
