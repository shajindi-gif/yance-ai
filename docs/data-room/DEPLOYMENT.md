# Deployment

Status: **Implemented reproducible container build; Partial production platform**.

## Implemented path

1. CI lints, typechecks, validates OpenAPI, applies and rolls back/forwards migrations, runs tests/evals/audits/E2E, verifies a logical restore, and builds frontend/backend containers: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).
2. Backend container runs as a non-root user: [`yance-ai/Dockerfile`](../../yance-ai/Dockerfile).
3. Frontend produces a standalone Next.js runtime: [`website/next.config.js`](../../website/next.config.js) and [`website/Dockerfile`](../../website/Dockerfile).
4. Production composition gates API/Agent-worker/document-worker startup on successful migrations and gates document work on the ClamAV service health check: [`yance-ai/docker-compose.prod.yml`](../../yance-ai/docker-compose.prod.yml).
5. Container jobs generate SPDX SBOMs, scan fixed high/critical vulnerabilities and confirm the runtime user is non-root.
6. CodeQL scans Python and JavaScript/TypeScript using security-extended queries: [`.github/workflows/codeql.yml`](../../.github/workflows/codeql.yml).
7. Release, rollback and restore checks are documented under [`docs/production-readiness/`](../production-readiness/).

## Required environment

Secrets and service endpoints come from environment variables documented in [`yance-ai/.env.production.example`](../../yance-ai/.env.production.example). No production secret values belong in the repository. Production startup requires `MALWARE_SCAN_MODE=required`, a configured `CLAMD_HOST`, and `DOCUMENT_OCR_ENABLED=true`; development can explicitly report scanning/OCR as disabled.

## Partial / planned

- **Partial:** repository provides a deployable topology, not evidence that a particular environment is currently running it.
- **Partial:** the ClamAV container, persisted signature database, outbound URL egress policy and real object-store ingestion path require the supplied [staging runbook](../production-readiness/DOCUMENT_INGESTION_RUNBOOK.md) before customer documents are accepted.
- **Implemented locally/CI:** logical backup and isolated restore verification. This is not evidence of managed backup scheduling.
- **Planned:** immutable production image-digest promotion, managed scheduled backups, blue/green rollout, autoscaling and multi-zone database configuration.
