# Technical Roadmap

Status: **Forward plan; items below are not shipped claims**.

## Next 30 days

- Connect the implemented regression/E2E/restore gates to protected-branch enforcement and a staging environment.
- Expand ingestion fixtures for DOCX/XLSX/URL edge cases.
- Add policy freshness monitoring and change-detection jobs.
- Establish staging telemetry dashboards and alert ownership.

## Days 31–60

- Run reviewed domain-expert evaluation sets and publish methodology with sample sizes.
- Add shared rate limiting and queue-depth-based worker scaling.
- Add SSO/SAML design and enterprise audit export.
- Execute external security assessment and remediate findings.

## Days 61–90

- Introduce submission-channel adapters behind human approval gates.
- Add organization-specific retrieval collections and feedback-driven eval sampling.
- Benchmark retrieval, workflow concurrency and renderer capacity.
- Define RTO/RPO from tested backup and restore evidence.

Sequencing is risk-driven: evidence correctness and tenant isolation precede autonomous external actions. Product milestones and remaining P0–P3 items are tracked in [`docs/investor-readiness/10_UPGRADE_ROADMAP.md`](../investor-readiness/10_UPGRADE_ROADMAP.md).
