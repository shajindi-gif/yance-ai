# Release-Candidate Risk Register

Review date: 2026-09-06. “Accepted” below means temporarily accepted for investor demo or controlled PoC; it does not mean accepted for enterprise GA.

## P0

No known open P0 was found in the Phase 11 local release checks. This is not a substitute for an external penetration test or production-environment review. Any confirmed tenant data leak, secret exposure, payment double-settlement or destructive migration becomes P0 immediately and blocks release.

## P1

| Risk | Existing control | Owner role | Target date | Acceptance |
|---|---|---|---|---|
| Database row-level security is not enabled | tenant predicates, ownership checks, cross-tenant API tests, scoped keys | CTO / Data Security | 2026-10-15 | Accepted for controlled PoC; not enterprise GA |
| SSO/SAML and automated provisioning are absent | RBAC, memberships, short-lived JWTs, API keys | Product + Identity Lead | 2026-11-15 | Accepted for SMB/PoC; blocks SSO-required deals |
| Hosted OpenTelemetry/log retention/alert delivery is not connected in repository evidence | structured request/run logs and admin trace views | Platform Lead | 2026-09-30 | Accepted only for local/staging demo |
| Reviewed real-world eval corpus is too small/not yet persisted as an accuracy claim | versioned datasets, hashes, review state, five eval families, explicit empty state | AI Quality Lead | 2026-10-31 | No accuracy marketing claim allowed |
| User-uploaded company document extraction still requires a production ingestion worker/provider integration | validated upload lifecycle, document records, company profile versioning | Agent Platform Lead | 2026-10-15 | Demo uses labelled deterministic data; real automation claim is limited |
| Managed backup scheduling and cross-region restore are not evidenced | locally tested logical restore and runbook | Platform Lead | 2026-09-30 | Blocks production data SLA |
| No external penetration test or compliance certification | CI scans, security boundaries, secret policy, secure defaults | Security Lead | 2026-11-30 | Must be disclosed in enterprise diligence |
| Container base images use version tags rather than repository-pinned digests | locked app dependencies, SBOM and image scanning | Platform + Security | 2026-09-30 | Accepted for CI; production deploy must record digests |
| External submission-channel execution is not shipped | persistent application workspace and human approval gates | Product Lead | 2026-12-05 | Product claims drafting/workflow, not autonomous filing |

## P2

- Shared/distributed rate limiting and queue-depth autoscaling.
- Policy freshness/change-detection jobs and source connector expansion.
- Organization-specific retrieval collections and learned reranking after evaluation evidence.
- PDF export coverage in the authenticated golden journey (demo endpoint already exercises the production renderer).
- WCAG/accessibility audit and continuous Core Web Vitals telemetry.
- Several legacy integration fixtures assume a pristine database; CI provides one, while repeated local full-suite runs must recreate the test database until per-test isolation is completed.

Risk status is reviewed at each release. Closing an item requires implementation evidence, tests and updated data-room documentation.
