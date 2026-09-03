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

## Slice 3 — Validated, replay-safe provider settlement

Status: implemented and tested; Phase 1 remains open.

### Changed

- Added an immutable `PaymentEvent` receipt ledger and additive migration
  `20260902_0010` with a unique provider/event boundary.
- Centralized payment settlement so an order is only marked paid after exact amount, currency,
  order, tenant and product validation.
- Serialized settlement on the order row, made provider event retries idempotent, and avoided
  duplicate entitlements or analytics on an already-settled order.
- Added Alipay application/seller verification, provider scoping, malformed-signature handling,
  CNY enforcement and protection against downgrading a completed payment.
- Added Stripe session payment-state, metadata, amount and currency validation before settlement.
- Removed buyer identifiers and full signed callback bodies from persisted payment responses;
  the receipt ledger stores a SHA-256 payload digest instead.
- `payment_completed` analytics is emitted only by successful server-validated settlement.

### Verification

- Touched-file Ruff gate: pass.
- Payment settlement and Phase 1 security regression subset: 15 passed.
- Added negative coverage for underpayment, currency mismatch and tenant/order mismatch.
- Added positive and replay coverage for one entitlement and one real analytics event.
- Database base-to-head remains pending the Phase 1 PostgreSQL + pgvector smoke gate.

## Slice 4 — Tenant provenance, upload integrity and truthful product surfaces

Status: implemented and regression-tested; Phase 1 remains open.

### Changed

- Authentication now rejects inactive users and inactive tenants before constructing a
  principal; tenant user listing is limited to owners/admins and admins cannot create owners.
- Global policy reads consistently allow only global rows or rows owned by the active tenant.
- Client-written analytics and Agent Run endpoints fail closed, while signup, company creation,
  document upload and provider settlement emit server-owned events at their real boundaries.
- Document uploads allow only PDF, DOCX, XLSX, CSV and TXT, enforce a configurable 25 MiB limit,
  and verify object-store size before completion; client checksums are not represented as
  server-verified.
- Orders now bind entitlement scope to a tenant-owned company or opportunity. Migration
  `20260903_0011` adds the resource fields and index without destructive schema changes.
- Migration `20260903_0012` backfills legacy nullable values, tightens ORM invariants and maps
  existing metadata columns/indexes instead of proposing destructive removals.
- Demo settlement uses a separate event name and cannot inflate real payment metrics.
- Public security, privacy, pricing, download, extension, policy, demo and product pages now
  distinguish code-backed facts, deployment-dependent controls, roadmap features and fictional
  examples. The claim register defines the evidence required to promote future claims.
- Frontend product and entitlement reads use the centralized API client; checkout pricing comes
  from the server catalog and payment redirects no longer imply that payment already settled.
- Ruff formatting and safe automatic modernization were applied to the backend; embedded
  HTML/CSS and migration SQL are excluded from line-length enforcement because automatic wrapping
  is unsafe.

### Verification

- Full backend suite: 28 passed.
- Next.js production build and TypeScript validation: pass for 26 routes.
- Alembic graph: one head at `20260903_0012`.
- PostgreSQL 18 + pgvector 0.8.6 base-to-head migration: pass.
- `alembic check` against the migrated database: pass with no new upgrade operations detected.

## Slice 5 — Dependency remediation and enforceable release gates

Status: locally verified; the hosted CI run is required before release.

### Changed

- Moved CI from the inert backend subdirectory to `.github/workflows/ci.yml`, where GitHub can
  execute it for pull requests and pushes to `main`.
- Added independent gates for backend lint/compile/tests, PostgreSQL + pgvector base-to-head
  migration, ORM/migration drift, frontend production dependency audit, production build,
  standalone runtime artifact, Python dependency audit, committed-history secret scan, and both
  production container builds.
- Removed the old structural JSON eval command from CI. It did not execute the product engine and
  therefore could not be represented as an Agent quality gate.
- Upgraded Next.js from 14.2.35 to 16.3.4 and React from 18 to 19.2.8 using the official staged
  codemods. The frontend is configured to emit the standalone artifact expected by its Dockerfile.
- Upgraded WeasyPrint to 69.x to remediate the redirect-based SSRF bypass and presentational-hint
  CSS injection advisories. Upgraded pytest to 9.0.3+ to remediate insecure temporary-directory
  handling.
- Added the Next.js 16 scroll behavior marker required by the existing global smooth-scroll CSS.

### Verification

- Backend Ruff and compile gates: pass.
- Full backend suite on Python 3.12: 28 passed; coverage 50.47%, above the new 50% floor.
- PDF/invoice hostile-input renderer suite after WeasyPrint 69 upgrade: 3 passed.
- Python installed-dependency audit: no known vulnerabilities found.
- npm production dependency audit: 0 vulnerabilities.
- Next.js 16.3.4 production build and TypeScript validation: pass for 26 routes.
- Standalone server artifact required by the frontend image: present.
- Manual browser smoke: `/`, `/pricing`, `/security`, `/success`, and `/dashboard` returned 200,
  rendered meaningful content, and showed no framework error overlay.
- Root workflow YAML parse and repository whitespace check: pass.
- Local container builds were not executed because the local container VM could not start. The
  root CI treats both image builds as mandatory and no release may bypass that hosted result.

## Phase 1 exit status

The Phase 1 implementation plan is complete in the working tree and all locally available gates
are green. Production release remains blocked until the root workflow has run successfully on the
remote repository, including full-history secret scanning and both container builds. Deployment
controls such as database RLS, isolated rendering workers, backup evidence, legal review, refunds,
and bank reconciliation are not claimed as complete; disabled or unsupported paths remain closed
until their later enterprise phases provide those controls.
