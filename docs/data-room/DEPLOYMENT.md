# Deployment

Status: **Implemented reproducible container build; Partial production platform**.

## Implemented path

1. CI lints, validates OpenAPI, applies migrations, checks model drift, runs tests/evals/audits, builds frontend/backend containers: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).
2. Backend container runs as a non-root user: [`yance-ai/Dockerfile`](../../yance-ai/Dockerfile).
3. Frontend produces a standalone Next.js runtime: [`website/next.config.js`](../../website/next.config.js) and [`website/Dockerfile`](../../website/Dockerfile).
4. Production composition gates API/worker startup on successful migrations: [`yance-ai/docker-compose.prod.yml`](../../yance-ai/docker-compose.prod.yml).
5. Release and rollback checks are documented: [`yance-ai/docs/releases/RELEASE_PROCESS.md`](../../yance-ai/docs/releases/RELEASE_PROCESS.md).

## Required environment

Secrets and service endpoints come from environment variables documented in [`yance-ai/.env.example`](../../yance-ai/.env.example). No production secret values belong in the repository.

## Partial / planned

- **Partial:** repository provides a deployable topology, not evidence that a particular environment is currently running it.
- **Planned:** managed backups with tested restore, blue/green rollout, autoscaling and multi-zone database configuration.
