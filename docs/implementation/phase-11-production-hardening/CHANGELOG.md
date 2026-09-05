# Phase 11 Changelog — Testing and Production Hardening

Date: 2026-09-06

## Delivered

- Classified the persisted registration-to-deliverable API/worker journey as an explicit E2E release gate.
- Made the golden journey self-cleaning and repeatable; it now targets its own queued workflow rather than unrelated database work.
- Added Playwright 1.63.0 and a Chromium `/demo` test covering synthetic-data disclosure, all seven workflow stages, exact-span evidence, Agent trace and DOCX download.
- Added frontend `typecheck` and `test:e2e` scripts.
- Added bounded concurrent HTTP smoke tooling that ignores ambient proxy variables and reports success, errors, throughput and p50/p95/p99.
- Added safe API response headers and API `no-store` behavior with regression tests.
- Extended CI with latest-migration rollback/forward, explicit E2E, latency smoke and PostgreSQL logical backup/restore verification.
- Added CodeQL security-extended analysis for Python and JavaScript/TypeScript.
- Added container SPDX JSON SBOM generation, fixed high/critical vulnerability blocking and non-root runtime inspection.
- Added SLO/alert, incident, backup/restore, release/rollback and dated risk-acceptance documentation.
- Updated deployment, observability and technical roadmap data-room material.
- Added the final `INVESTOR_READY_REPORT.md` with verified results and explicit claim boundaries.

## No migration

No schema change was required. Local verification applied all migrations through `20260905_0020`, downgraded one revision, upgraded to head and restored a logical backup to an isolated database.

## Verification snapshot

- Backend: 53 tests passed; 77.91% line coverage.
- Golden API/worker E2E: passed twice consecutively.
- Chromium investor demo E2E: 1 passed.
- Deterministic evals: 11/11 release-gate cases passed across five synthetic unreviewed datasets; not an accuracy claim.
- Local bounded smoke: 100/100 health requests succeeded at concurrency 10; p95 9.75 ms; not a capacity benchmark.
- Migration rollback/forward: passed.
- Logical backup/restore with revision/key-count checks: passed.
- Full-suite repeat on an already populated test database exposed legacy global-count/queue fixture assumptions; the final gate passed on the same pristine-database contract used by CI, and per-test isolation is recorded as P2.

## Remaining release work

Remote CI execution, protected-branch enforcement, hosted telemetry, managed backup scheduling, image digest promotion and external security testing require the target production platform. Owners and dates are in `docs/production-readiness/RISK_ACCEPTANCE.md`.
