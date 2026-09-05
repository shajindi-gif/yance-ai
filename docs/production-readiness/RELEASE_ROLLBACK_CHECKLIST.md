# Release and Rollback Checklist

## Before merge

- [ ] Change has a bounded scope, migration plan and rollback impact.
- [ ] Ruff, Python compile, OpenAPI drift, pytest coverage gate and deterministic eval gate pass.
- [ ] Frontend TypeScript and production build pass.
- [ ] API/worker E2E and Chromium investor-demo E2E pass.
- [ ] Dependency, secret, CodeQL and container vulnerability scans pass.
- [ ] Container SBOMs are retained and runtime user is non-root.
- [ ] New analytics/metrics are database-derived; demo/sample data is labelled and excluded from investor metrics.
- [ ] P0 findings are zero; unresolved P1 items have role owner, target date and explicit acceptance.

## Staging

- [ ] Deploy immutable image digests, not mutable tags.
- [ ] Apply migration with recorded before/after revision.
- [ ] Verify liveness, readiness, login, tenant isolation, one policy scan and one artifact download.
- [ ] Verify request/run correlation, alert delivery and cost/usage recording.
- [ ] Run logical backup/restore drill when the release changes schema or data semantics.
- [ ] Record release identifier, image digests, migration revision, verifier and timestamp.

## Production

- [ ] Confirm approved change window, incident owner and communication channel.
- [ ] Take/verify pre-change backup when rollback could touch data.
- [ ] Apply migrations once through the migration job; API/workers start only after success.
- [ ] Observe readiness, 5xx, p95 latency, DB connections, queue age and Agent failure rate.
- [ ] Keep demo features disabled and production secrets validated.

## Rollback decision

Rollback for sustained readiness failure, material regression, security boundary failure, payment inconsistency or unexpected migration behavior. Prefer feature-flag/worker pause for isolated features. Application rollback is safe only if the old version is schema-compatible. Database downgrade requires explicit migration review, a verified backup and an isolated rehearsal.

## Evidence to retain

CI run, approvals, SBOMs, vulnerability results, image digests, migration output, smoke/E2E output, restore evidence, incident/change ticket and post-release observation window.
