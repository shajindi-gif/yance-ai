# PostgreSQL Backup and Restore Runbook

Status: **logical backup/restore procedure tested locally in Phase 11; managed-production scheduling remains environment work**.

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
