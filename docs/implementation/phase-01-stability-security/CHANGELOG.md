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

## Slice 2 — Safe document rendering and eligibility hard gates

Status: implemented and tested; Phase 1 remains open.

### Changed

- Added a shared HTML escaping boundary and a fail-closed WeasyPrint URL fetcher.
- Escaped company, policy, evidence, invoice and line-item content before HTML rendering.
- Removed temporary HTML files and the subprocess fallback that bypassed the URL policy.
- Replaced the broken invoice `str.format()` template with `string.Template`; tests proved the
  previous implementation failed on CSS braces before producing a PDF.
- Invoice output filenames now use server-generated UUIDs rather than invoice content.
- Removed unsupported deployment/encryption claims from generated report footers.
- Safety accidents, environmental violations and social-credit requirements are blocking
  eligibility criteria and cannot be softened into an eligible result.

### Verification

- Added renderer payload tests for `<script>`, remote image and `file://` inputs.
- Added hard-gate tests for safety, environment, credit and insufficient evidence.
- Full backend suite: 13 passed; coverage increased from 45% to 49%.
