# Phase 1 Changelog

## Slice 1 — Commerce, configuration, tenant scope, schema alignment

Status: implemented and unit-tested; Phase 1 remains open.

### Changed

- Demo payment and task direct-pay are disabled by default and rejected in production.
- Product rows, not client amounts, determine newly created order prices.
- The generic payment-record creation endpoint is disabled pending provider event handling.
- Invoice creation persists the Invoice instead of re-adding the Order.
- Company financial identifiers no longer have repository defaults; bank details require
  authenticated owner/admin access and complete environment configuration.
- Broken bank receipt verification endpoints fail closed until a platform finance role and
  payment ledger are implemented.
- Policy evaluation only reads global policies or policies owned by the current tenant.
- The existing task operations view is tenant-scoped.
- Sanitized `.env.example` files are tracked and a truthful root `SECURITY.md` is present.
- Migration `20260902_0009` adds missing Task progress/stage and Deliverable timestamps.

### Verification

- Python 3.12 compile: pass.
- Pytest: 7 passed; total coverage remains 45% and is not accepted as sufficient.
- Next.js production build: pass for 25 routes, with the existing Google Fonts
  optimization warning.
- Alembic graph: one head at `20260902_0009`.
- Database base-to-head: pending a PostgreSQL instance with pgvector.
- Full Ruff: still red from the audited legacy baseline; this slice removed import errors in
  touched files but does not claim Phase 1 lint completion.

### Remaining Phase 1 work

- Provider webhook ledger, entitlement atomicity and payment replay tests.
- PDF/invoice HTML escaping and network/file fetch denial.
- Eligibility hard-gate regression and mandatory review.
- External claim corrections, root CI, dependency remediation and full migration smoke.
