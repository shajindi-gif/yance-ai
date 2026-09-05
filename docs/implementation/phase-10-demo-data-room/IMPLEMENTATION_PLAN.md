# Phase 10 — Investor Demo + Data Room Implementation Plan

Date: 2026-09-05  
Branch: `feature/investor-grade-upgrade`

## Objective

Deliver a three-to-five-minute, evidence-first investor walkthrough backed by the product's real domain models and document renderer, while keeping all synthetic data out of customer, revenue, activity, cost, and quality metrics. Publish an evidence-linked engineering data room that distinguishes implemented, partial, and planned capabilities.

## Audit findings

- `/demo` redirects to registration and does not demonstrate the product workflow.
- The legacy `scripts/seed_demo_companies.py` writes fabricated paid orders, payments, invoices, entitlements, analytics events, opportunity scores, and revenue output.
- Tenants do not have a database-level demo classification, so metric queries cannot reliably exclude synthetic records.
- The production domain model already supports company profiles, immutable profile versions, policies, structured rules, scans, eligibility results, evidence, applications, requirements, tasks, agent traces, and versioned artifacts.
- The artifact renderer already produces DOCX, PDF, XLSX, and JSON. Phase 10 will reuse it instead of presenting a UI-only download.
- `/docs/data-room/` does not exist.

## Truth and isolation boundary

1. Add `Tenant.is_demo` and `Tenant.demo_dataset_key` as the authoritative isolation boundary.
2. Add `DemoScenario` as a platform-owned index that links only to real tenant-scoped domain rows.
3. Public demo endpoints fail closed unless both the scenario is published and its tenant has `is_demo=true`.
4. Synthetic policies are tenant-private, use `.invalid` source URLs, and are labelled `DEMO / synthetic`; they cannot enter the shared policy corpus.
5. The demo seeder creates no users, memberships, orders, payments, invoices, subscriptions, entitlements, API keys, audit events, analytics events, or evaluation results.
6. Investor metrics and system-health metrics exclude demo tenants at query time.
7. Documentation labels claims as **Implemented**, **Partial**, or **Planned** and links each implemented claim to repository evidence.

## Workflow implemented

`Company Profile → Imported Document → Policy Scan → Eligibility → Evidence → Application → Generated Document`

Each scenario uses persisted records and an actual rendered artifact. The public UI is read-only and contains an always-visible synthetic-data notice.

## Planned files

### Database and backend

- `yance-ai/alembic/versions/20260905_0020_investor_demo.py`
- `yance-ai/app/models/models.py`
- `yance-ai/app/services/demo/scenarios.py`
- `yance-ai/app/api/routes/demo.py`
- `yance-ai/app/api/router.py`
- `yance-ai/app/services/admin/metrics.py`
- `yance-ai/scripts/seed_investor_demo.py`
- `yance-ai/scripts/seed_demo_companies.py`

### Frontend

- `website/app/demo/page.tsx`
- `website/app/demo/DemoExperience.tsx`
- `website/app/demo/Demo.module.css`
- `website/lib/api.ts`

### Tests and documentation

- `yance-ai/tests/test_investor_demo.py`
- `docs/data-room/README.md`
- `docs/data-room/SYSTEM_ARCHITECTURE.md`
- `docs/data-room/TECH_STACK.md`
- `docs/data-room/AGENT_ARCHITECTURE.md`
- `docs/data-room/RAG_ARCHITECTURE.md`
- `docs/data-room/SECURITY.md`
- `docs/data-room/DATA_MODEL.md`
- `docs/data-room/MULTI_TENANCY.md`
- `docs/data-room/EVALUATION.md`
- `docs/data-room/OBSERVABILITY.md`
- `docs/data-room/DEPLOYMENT.md`
- `docs/data-room/SCALABILITY.md`
- `docs/data-room/TECHNICAL_ROADMAP.md`
- `DEMO_SCRIPT.md`
- `docs/implementation/phase-10-demo-data-room/CHANGELOG.md`

## Migration strategy

- Forward-only additive migration.
- `tenants.is_demo` is non-null with a server default of false.
- `tenants.demo_dataset_key` is nullable and unique; production tenants remain unchanged.
- `demo_scenarios` references existing domain entities and is cascade-deleted with its demo tenant.
- Downgrade removes only Phase 10 objects.

## Verification gate

- Migration upgrade succeeds from Phase 9 and schema reaches head.
- Seeder is idempotent and creates exactly five explicitly synthetic scenarios.
- Public list/detail/download endpoints expose only published demo-tenant records.
- Evidence quotes are exact substrings of the persisted synthetic source text.
- All four artifact formats are rendered by the production renderer.
- Investor totals, funnel, revenue, cost, and quality metrics are unchanged by seeding.
- Backend lint, type checks, tests, security audit, frontend lint/typecheck/tests/build pass.
- Browser walkthrough proves a complete demo path, responsive states, retry/error handling, and a working DOCX download.

