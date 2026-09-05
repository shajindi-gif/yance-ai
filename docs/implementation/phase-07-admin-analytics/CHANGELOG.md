# Phase 7 — Admin, Analytics and Investor Metrics Changelog

Date: 2026-09-05

## Outcome

Yance now has a platform-operator control plane that is separate from tenant RBAC and is backed
only by persisted server records. Product milestones are recorded through a centralized,
tenant-scoped analytics path, and the internal investor page presents reproducible definitions,
scope, freshness, and explicit unavailable states instead of inferred commercial or quality
claims.

## Authority, data and migration

- Added `User.is_platform_admin`; public registration cannot assign it, and Tenant Owner/Admin
  roles do not grant cross-tenant access.
- Added an explicit Tenant `account_stage` with an `unclassified` default so PoC counts are never
  inferred from names, emails, or activity.
- Added analytics provenance, request correlation, and optional tenant-scoped idempotency keys.
  Existing rows remain compatible and no synthetic keys were backfilled.
- Added tenant-owned Feedback with authenticated creation and platform-admin review states.
- Added the additive `20260904_0017` migration and a server-side promotion script that requires an
  exact tenant slug and email plus an explicit grant or revoke flag.

## Analytics and operating metrics

- Centralized server-owned events for registrations, logins, company creation/profile completion,
  document uploads, policy scans, opportunity opens, Application creation, generated artifacts,
  checkout starts, paid settlement, and reports.
- Opportunity opens are deduplicated per user, opportunity, and UTC day. Concurrent duplicate
  inserts resolve as a successful no-op rather than a user-visible failure.
- Investor totals now read users, active users, organizations, companies, scans, Applications,
  generated reports/documents, Agent Runs, explicit PoC stages, paid orders, model cost, and
  cost/run directly from the database.
- Revenue is summed only from paid Orders and remains separated by currency. No exchange-rate
  conversion or MRR inference is performed.
- The milestone funnel counts distinct organizations with server-owned events and is labelled as
  an all-time milestone funnel, not cohort retention.
- System health exposes current queues, running/stale Agent Runs, recent failures, ingestion state,
  feedback, and database readiness. Historical API latency remains explicitly unavailable because
  it is not durably stored yet.

## Platform API and product surface

- Added platform-admin-only overview, investor metrics, system health, safe resource directories,
  account-stage updates, and feedback review endpoints.
- Safe resource projections omit password hashes, payment provider payloads, object-storage keys,
  and free-form Agent inputs/outputs.
- Added `/admin` with persisted totals, a 30-day Agent execution trend, operational health, and
  paginated Users, Organizations, Companies, Agent Runs, Workflow Runs, LLM Usage, Costs,
  Documents, Policies, Evals, Errors, Billing, Feedback, and Analytics views.
- Added `/admin/investor-metrics` with every requested currently measurable metric, currency-aware
  revenue, a reproducible funnel, metric definitions, and availability disclosure.
- Admin navigation appears only after `/auth/me` reports platform authority; backend enforcement
  remains the security boundary.
- The Evals view displays `No evaluation data yet.` until Phase 8 writes real benchmark results.

## Verification

- PostgreSQL 18 + pgvector database migrated from revision zero through `20260904_0017`.
- The Phase 7 migration downgraded to `20260904_0016`, upgraded to head on populated test data, and
  passed `alembic check` with no model/schema drift.
- Full backend suite on a freshly migrated database: 41 passed; total coverage 73.05% against the
  enforced 50% CI floor.
- Admin tests prove platform/tenant authority separation, exact database aggregation, distinct-org
  funnel counts, currency-safe paid revenue, event deduplication, safe projections, feedback
  persistence, account-stage updates, and honest availability flags.
- Backend Ruff and Python compilation: passed.
- Next.js 16.3.4 production build and TypeScript validation: passed; 32 routes generated.
- Browser verification against the real API/database covered platform login, Admin totals, system
  health, safe user resources, the empty Eval state, investor metrics, funnel definitions, and
  unavailable metrics. No browser console warnings/errors or horizontal overflow were found.

## Code quality note

- Ruff formatting was applied to the backend tree while validating this phase. This produced
  mechanical formatting-only changes in several Phase 3–6 workflow, policy, migration, and test
  files; their behavior and schema operations are unchanged and the full regression suite passes.

## Intentional deferrals

- Phase 8 still needs reviewed benchmark datasets, persisted Evaluation records, scoring jobs, and
  quality dashboards. No accuracy, hallucination, citation, or pass-rate number is shown yet.
- Subscriptions, invoices, quota enforcement, MRR, retention cohorts, CRM attribution, and revenue
  recognition rules remain future commercial-system work.
- Historical API latency needs a durable metrics backend before it can be reported truthfully.
- Support impersonation, tenant switching, SSO, alert delivery, and policy publishing workflows are
  not introduced by this phase.
