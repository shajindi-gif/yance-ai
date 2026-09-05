# Phase 9 — Billing and Enterprise Changelog

Date: 2026-09-05

## Outcome

Yance now has a server-authoritative subscription and usage-control foundation plus the first
operable enterprise data-governance controls. Every tenant is resolved to a database-backed plan,
subscription period and quota before metered work is accepted. API access, exports, retention,
deletion requests and feature rollouts are tenant-scoped and audited.

This phase does not claim a paid recurring-billing integration. Only the Free price is configured;
Pro, Business and Enterprise intentionally expose no purchasable price until a real provider price
and commercial configuration exist.

## Billing catalog and subscriptions

- Added versioned Plan, PriceVersion, Subscription and SubscriptionItem records without replacing
  the existing replay-safe one-time Order/Payment/Entitlement flow.
- Added Free, Pro, Business and Enterprise product configurations with explicit capacity fields.
  These are product limits, not evidence of customers, revenue or adoption.
- Free tenants are provisioned lazily under a locked tenant row. The billing page reads the active
  subscription period, plan, limits, usage, budgets, orders and tax-invoice references from the
  backend.
- Paid tiers have no active PriceVersion. The UI displays `价格未配置` and disables the recurring
  checkout claim instead of inventing a monthly fee or mock subscription.

## Usage, quotas and budgets

- Added eight meters: policy scans, companies, reports, uploaded documents, generated documents,
  Agent Runs, users and storage bytes.
- Resource quotas reconcile to live tenant-owned rows; event quotas use idempotent UsageRecords in
  the same transaction as the product mutation.
- Enforced quotas at company/user creation, upload presign, policy scan/Agent Run, report generation
  and generated-application-document paths.
- Report allowance is checked before retrieval/model execution; duplicate report idempotency keys
  are rejected when no persisted response can be replayed. Usage idempotency is evaluated only
  after the tenant subscription lock, closing the concurrent check-before-lock race.
- Added organization, user and workflow hard budgets. A budget may narrow a plan allowance but can
  never expand it. Quota rejection returns a structured HTTP 429 with current use, requested units,
  effective limit and period reset time.

## Enterprise controls

- API Keys use one-time `yance_live_...` secrets and store only a peppered HMAC-SHA256 digest.
  Read/write scopes, expiry, revocation and last-use are enforced. API Keys cannot access Admin,
  billing, membership, payments or enterprise control-plane routes.
- Membership is the authoritative tenant role during authentication; a stale role embedded in a
  user record or token cannot elevate the active Membership.
- Added configurable retention records and legal holds. Automated retention enforcement is marked
  unavailable until a deployment worker exists.
- Added checksummed workspace JSON exports with explicit exclusion of password/API-key hashes,
  raw payment responses and document object-storage keys.
- Added Owner-only deletion scheduling and cancellation with a seven-day cooling period. Legal hold
  blocks scheduling. Cross-store/log/backup/provider propagation remains an explicit blocker, so a
  request is never misrepresented as completed erasure.
- Added hash-linked enterprise audit records carrying action, actor, tenant, target, result, reason,
  request ID and previous/entry hashes without storing raw secrets or document content.
- Added platform-admin Feature Flag configuration, tenant overrides and override removal. Effective
  flags are resolved server-side and every tenant override mutation is written to that tenant's
  audit chain.

## Product UI

- Added `/billing` with real usage bars, current subscription, database plan catalog, honest paid
  configuration status, and empty real-transaction state.
- Added `/settings` for one-time API Key issuance/revocation, retention visibility, safe workspace
  export and deletion scheduling/cancellation.
- Added billing and enterprise settings to the authenticated workspace navigation.
- Added explicit retry controls for empty failed-load states. Mobile-width browser inspection
  confirmed that the new controls remain readable and operable.

## Verification

- Fresh PostgreSQL database migrated from revision zero through `20260905_0019`.
- Populated database downgraded to `20260905_0018`, upgraded back to head and passed `alembic check`
  with no model/schema drift.
- Backend Ruff and Python compilation passed.
- OpenAPI contract was regenerated and passed the current-contract check.
- Full backend suite on a fresh isolated database: 50 passed with 77.16% application coverage
  against the 50% CI floor. Tests cover quotas, budget narrowing,
  usage idempotency, Membership authority, API Key secret handling/scopes/revocation, tenant-safe
  export, legal hold/deletion cooling, audit hashes and platform-managed tenant Feature Flags.
- Next.js production build and TypeScript validation passed with 35 routes, including `/billing`
  and `/settings`.
- Production dependency audits reported zero known npm or Python package vulnerabilities at the
  time of verification.
- Browser verification passed for login, dashboard, billing and enterprise settings. It exercised
  one-time API Key display and workspace export; reload confirmed the original key is not returned
  again. There was no framework error overlay or browser error log. A transient request failure
  during first-time development compilation was recoverable, and the affected pages now expose a
  manual retry control.

## Intentional deferrals

- Paid recurring checkout, provider subscription webhooks, proration, refunds, dunning/grace-state
  transitions, tax-invoice issuance and reconciliation require real provider/merchant configuration
  and remain open. No paid plan is currently self-purchasable.
- Retention execution and deletion propagation across primary data, object storage, vector indexes,
  logs, analytics, backups and model providers require deployment-specific workers and evidence.
- API Key rotation, outbound webhooks, SSO/SAML/OIDC, SCIM, MFA enforcement and database RLS remain
  enterprise-hardening work; current isolation still relies on application-scoped queries plus
  negative tests.
- Usage metering currently commits integer units after successful application mutations; reservation
  and final settlement for long-running/concurrent token workloads remain a future cost-control
  improvement.
- Phase 10 will add strictly isolated, visibly labelled demo datasets and evidence-linked data-room
  materials. Product configuration and test records must not be presented as traction.
