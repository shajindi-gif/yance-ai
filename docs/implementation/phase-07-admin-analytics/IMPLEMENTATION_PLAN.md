# Phase 7 — Admin, Analytics and Investor Metrics Implementation Plan

## Objective

Create a platform-admin-only operating control plane backed exclusively by persisted records, and
make the product funnel measurable through server-owned, deduplicated analytics events. Missing
commercial or quality data must remain visibly unavailable rather than being inferred or mocked.

## Current-state findings

- Owner/Admin roles are tenant roles; there is no separate platform-operator authority for
  cross-tenant data.
- `/analytics/stats` is a tenant-level seven-day counter embedded in a legacy demo router. It mixes
  product operations with an advertised model catalogue and cannot serve investor diligence.
- Server-owned events already cover signup, company creation/profile completion, uploads, scan
  start/completion, Application creation, generated documents, reports, and settled payments.
  Opportunity opens and checkout starts are not recorded.
- Analytics events have no explicit provenance or idempotency key.
- There is no Admin UI, investor metrics page, platform resource directory, feedback store, or
  operational queue/error view.
- LLM cost and latency exist on AgentRun/WorkflowRun and must be aggregated directly; deterministic
  runs correctly contribute zero model cost.
- PoC account classification is not stored. It cannot be reported until an explicit account stage
  exists.

## Metric model

Primary operating outcomes:

1. Activated organizations: distinct organizations reaching `company_profile_completed`.
2. Executing organizations: distinct organizations reaching `application_created`.
3. Paying customers and recognized checkout revenue: organizations/orders with server-validated
   paid state, grouped by currency.

Drivers:

- registrations, company profiles, policy scans, generated documents and completed Agent Runs;
- 30-day active users, defined as distinct users with a server-owned event during the trailing
  30-day window.

Guardrails:

- failed Agent Runs, unresolved Agent errors, queue depth, average latency, model cost/run and
  event provenance coverage.

No targets, growth rates, accuracy figures, retention claims, or revenue conversions are created
without historical data and reviewed business definitions.

## Deliverable slice

1. Add a persisted `is_platform_admin` authority independent of tenant RBAC.
2. Add Tenant account stage (`unclassified`, `poc`, `customer`, `churned`, `internal`) so PoC
   counts are explicit and default to unknown.
3. Add analytics `source`, `event_key`, and `request_id`; keep legacy events compatible and enforce
   tenant-scoped deduplication when a key is supplied.
4. Add tenant-owned Feedback with authenticated creation and platform-admin review status.
5. Centralize server-owned event creation and add real login, opportunity-opened and
   checkout-started instrumentation.
6. Add platform-admin APIs for overview, investor metrics, resource directories, system health,
   analytics event inspection, feedback review, and account-stage updates.
7. Define every investor metric beside its database source, scope, window and availability.
8. Build `/admin` and `/admin/investor-metrics` with source/freshness labels, honest empty states,
   a 30-day execution trend, conversion funnel, operational errors, and paginated resource views.
9. Expose Admin navigation only after `/auth/me` confirms platform authority; backend authorization
   remains the security boundary.
10. Add additive migration, permission/aggregation/event tests, OpenAPI refresh, production build,
    browser verification and changelog.

## Planned files

- `yance-ai/app/models/models.py`
- `yance-ai/alembic/versions/20260904_0017_admin_analytics.py`
- `yance-ai/app/api/deps.py`
- `yance-ai/app/api/router.py`
- `yance-ai/app/api/routes/admin.py`
- `yance-ai/app/api/routes/analytics.py`
- `yance-ai/app/api/routes/auth.py`
- `yance-ai/app/api/routes/commerce.py`
- `yance-ai/app/api/routes/workflow.py`
- `yance-ai/app/schemas/schemas.py`
- `yance-ai/app/services/analytics/events.py`
- `yance-ai/app/services/admin/metrics.py`
- `yance-ai/scripts/set_platform_admin.py`
- relevant existing event producers and backend tests
- `yance-ai/docs/openapi.json`
- `website/lib/api.ts`
- `website/lib/navigation.ts`
- `website/components/workspace/AppShell.tsx`
- `website/components/workspace/AppShell.module.css`
- `website/components/workspace/AdminDashboard.module.css`
- `website/app/admin/page.tsx`
- `website/app/admin/investor-metrics/page.tsx`
- `docs/investor-readiness/02_PRODUCT_AUDIT.md`
- `docs/implementation/phase-07-admin-analytics/CHANGELOG.md`

## Compatibility and migration

- Migration is additive. Existing users remain non-platform-admin and existing tenants remain
  `unclassified`; neither status is inferred from names, emails, order history, or demo data.
- Existing analytics rows are backfilled as `source=server` because the client-write endpoint has
  already been fail-closed. They do not receive fabricated event keys or request identifiers.
- Tenant Owner/Admin permissions remain unchanged and do not grant platform-wide access.
- Existing `/analytics/stats` remains available for compatibility but is not used as the investor
  source of truth.

## Release gates

- Tenant admins and ordinary members receive 403 from every platform-admin endpoint.
- Platform admin resource payloads exclude password hashes, raw payment payloads, document object
  keys, and free-form Agent inputs/outputs.
- Counts reconcile to inserted database fixtures, funnel counts use distinct organizations, and
  revenue remains currency-separated.
- Event deduplication prevents repeated opportunity-open and checkout-start events from inflating
  the funnel.
- Empty database states render zero or `Not tracked`; no demo values are substituted.
- Base-to-head migration, populated downgrade/upgrade, Alembic drift, full backend suite with
  coverage floor, OpenAPI snapshot, Next.js build and browser checks pass.

## Intentional boundaries

- This phase does not implement subscriptions, quota enforcement, invoices reconciliation, SSO,
  support impersonation, or tenant switching.
- API request latency remains available in structured logs but is not falsely reconstructed as a
  historical dashboard metric without a durable telemetry store.
- Evaluation accuracy and hallucination metrics remain unavailable until Phase 8 runs reviewed
  benchmark datasets.
- Platform-admin promotion is an operational database/management action; public registration can
  never self-assign it.
