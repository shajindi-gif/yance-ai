# Phase 11 — Testing and Production Hardening

## Objective

Turn the completed investor demo and production candidate into a repeatable release candidate with explicit end-to-end, migration, restore, security, performance, and operational gates. No synthetic benchmark is presented as production performance or model accuracy.

## Release gates

1. The API/worker golden journey covers registration, company profile, document upload, policy scan, persisted agent execution, eligibility/evidence, application creation, human review, generated artifacts, and downloads.
2. The browser investor journey validates the clearly labelled synthetic `/demo` experience and a downloadable deliverable.
3. CI runs lint, Python compilation, OpenAPI drift, forward migration, rollback/forward migration, model alignment, unit/integration/E2E tests, deterministic evaluation, frontend typecheck/build, dependency/secret/SAST checks, container build/SBOM/vulnerability scan, and database backup/restore verification.
4. Runtime responses carry safe security headers and request correlation without logging sensitive payloads.
5. Operations documentation defines SLOs, alerts, release/rollback, incident response, backup/restore, and accepted P1 risks with role owners and dates.
6. The final investor readiness report distinguishes implemented controls, locally verified results, demo-only data, and remaining risks.

## Planned files

### Tests and executable verification

- `yance-ai/tests/test_core_workflow.py`
- `yance-ai/pyproject.toml`
- `yance-ai/scripts/load_smoke.py`
- `website/package.json`
- `website/package-lock.json`
- `website/playwright.config.ts`
- `website/e2e/investor-demo.spec.ts`

### Runtime and delivery hardening

- `yance-ai/app/main.py`
- `.github/workflows/ci.yml`
- `.github/workflows/codeql.yml`

### Operations and diligence material

- `docs/production-readiness/SLO_AND_ALERTS.md`
- `docs/production-readiness/INCIDENT_RESPONSE.md`
- `docs/production-readiness/BACKUP_RESTORE_RUNBOOK.md`
- `docs/production-readiness/RELEASE_ROLLBACK_CHECKLIST.md`
- `docs/production-readiness/RISK_ACCEPTANCE.md`
- `docs/data-room/DEPLOYMENT.md`
- `docs/data-room/OBSERVABILITY.md`
- `INVESTOR_READY_REPORT.md`
- `DEMO_SCRIPT.md`
- `docs/implementation/phase-11-production-hardening/CHANGELOG.md`

## Migration strategy

No schema change is planned. The phase verifies both `upgrade head` and a one-revision rollback/forward cycle against PostgreSQL, then performs a logical backup and restore into an isolated CI database. If implementation discovers a required schema change, it must be additive and added to this plan before code changes.

## Verification

- Backend lint, compile, OpenAPI snapshot, migration alignment, full pytest suite with coverage.
- E2E marker gate and deterministic five-part eval gate.
- Frontend TypeScript check and production build.
- Playwright investor-demo flow against live frontend/API with synthetic seed.
- Parameterized HTTP load smoke with observed p50/p95/p99 and an explicit, generous release threshold.
- Docker image builds, SBOM generation, vulnerability scan, and non-root runtime inspection.
- Manual browser review of `/demo`, `/dashboard`, `/applications`, `/admin`, and `/admin/evals` where credentials/data permit.

## Non-goals

- Claiming production-scale load capacity from local or CI smoke tests.
- Claiming policy/eligibility accuracy from synthetic deterministic evals.
- Introducing a new cloud vendor, payment provider, or observability SaaS.
- Destructive schema redesign or replacement of the existing stack.
