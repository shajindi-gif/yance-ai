# Phase 9 — Billing and Enterprise Implementation Plan

Date: 2026-09-05

## Objective

Add a server-authoritative subscription, usage and enterprise-control layer without replacing the
existing replay-safe one-time payment flow. Free, Pro, Business and Enterprise become versioned
database plans with explicit limits; paid checkout remains unavailable until an active price and
provider price identifier are configured.

## Current-state findings

- Product, Order, Payment, provider-event, tax Invoice and Entitlement support replay-safe one-time
  settlement, but there is no recurring Subscription or historical plan price.
- Users, companies, uploads, scans, reports, generated documents, Agent Runs and storage are not
  constrained by a shared tenant quota.
- Membership roles exist, but enterprise API keys, retention settings, export/deletion requests and
  feature flags do not.
- AuditLog exists as a passive table and is not consistently written by enterprise mutations.
- The current pricing page is an authoritative one-time Product catalog; it must not invent monthly
  prices while subscription price versions are absent.

## Delivery slice

1. Add Plan, PriceVersion, Subscription and SubscriptionItem with additive migration and immutable
   price history.
2. Add UsageMeter, UsageRecord and UsageBudget. Enforce plan and budget limits at real write paths;
   idempotent records and locked subscriptions prevent repeat consumption.
3. Seed only product configuration: four plan definitions and eight meter definitions. Free has a
   zero price; paid tiers have no fabricated price and use contact/configuration status.
4. Add a billing overview API that reconciles subscription, current-period usage, limits, budgets,
   one-time orders and tax invoices from database records.
5. Add API-key create/list/revoke with one-time secret display, peppered hashes, scopes, expiry and
   last-used metadata. Keys cannot access billing, admin, membership or enterprise-control routes.
6. Add RetentionPolicy, ExportJob and DeletionRequest. Export produces a checksummed safe JSON
   snapshot; deletion is a scheduled request with legal-hold/cooling-period checks, not a fake
   immediate purge.
7. Add FeatureFlag and TenantFeatureFlag with effective tenant evaluation and platform-admin
   management.
8. Extend AuditLog fields and centralize append-only enterprise mutation records without storing
   API secrets, document contents or payment payloads.
9. Add `/billing` and `/settings` workspace pages with honest unavailable/configuration states.
10. Add RBAC, isolation, quota, idempotency, key-hashing, export-safety, retention/legal-hold and
    feature-flag tests.

## Quota semantics

- Resource meters (`companies`, `users`, `documents`, `storage_bytes`) use authoritative live table
  counts under a locked tenant subscription.
- Event meters (`policy_scans`, `reports`, `generated_documents`, `agent_runs`) use immutable,
  tenant-scoped UsageRecords inside the same transaction as the product mutation.
- Limits are integer units per subscription period. `null` means contract-defined/unlimited and is
  shown as such; missing limits never silently become unlimited.
- Usage errors return a structured 429 response with meter, used, requested, limit and reset time.
- User/org/workflow UsageBudgets can only reduce a plan allowance, never expand it.

## Plan truthfulness policy

- Free is self-provisioned for tenants that have no subscription.
- Pro, Business and Enterprise limits are initial product configuration, not customer usage or
  commercial traction.
- Paid tiers expose no currency amount until an active PriceVersion exists. The UI must say pricing
  is not configured/contact sales rather than substituting a static number.
- Subscription states are `active`, `past_due`, `grace_period`, `canceled` or `incomplete`; only
  active/grace access is usable. Provider webhooks remain signature-verified and replay-safe.

## Planned files

- `yance-ai/app/models/models.py`
- `yance-ai/alembic/versions/20260905_0019_billing_enterprise.py`
- `yance-ai/app/core/config.py`
- `yance-ai/app/api/deps.py`
- `yance-ai/app/api/router.py`
- `yance-ai/app/api/routes/billing.py`
- `yance-ai/app/api/routes/enterprise.py`
- `yance-ai/app/api/routes/{companies,documents,tenants,workflow}.py`
- `yance-ai/app/services/billing/{catalog,usage}.py`
- `yance-ai/app/services/enterprise/{api_keys,audit,exports,flags}.py`
- `yance-ai/app/schemas/schemas.py`
- `yance-ai/tests/test_billing_enterprise.py`
- `website/lib/{api,navigation}.ts`
- `website/app/billing/page.tsx`
- `website/app/settings/page.tsx`
- workspace CSS and audit/changelog documents

## Release gates

- Base-to-head and populated downgrade/upgrade migrations pass with no Alembic drift.
- Free subscription provisioning and all quota decisions reconcile to stored plan/version/usage.
- Duplicate idempotency keys do not consume twice; concurrent paths lock the subscription row.
- Owner/Admin/Member/Viewer and API-key scope matrices pass, including cross-tenant denial.
- Raw API keys are returned once and never stored or listed; revoked/expired keys fail closed.
- Export contains no password hash, API key hash, payment raw response or document object key.
- Legal hold blocks deletion scheduling; no endpoint claims full deletion before propagation exists.
- Full backend tests, coverage floor, OpenAPI snapshot, Next.js production build and browser checks
  pass before the phase commit.

## Intentional boundaries

- No paid plan can be self-purchased until a real PriceVersion and provider identifier are
  configured. This phase will not fake a Stripe/Alipay subscription.
- SAML/SCIM/MFA enforcement needs an external identity provider and remains capability metadata,
  not a pretend integration.
- Backup/provider-log erasure requires deployment-specific workers and retention evidence. The
  deletion workflow will expose these blockers instead of reporting a false completed purge.
