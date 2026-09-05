# Phase 10 — Investor Demo + Data Room Changelog

Date: 2026-09-05

## Delivered

- Added database-level demo isolation with `Tenant.is_demo`, a unique `demo_dataset_key`, and a platform-owned `DemoScenario` index.
- Replaced the destructive legacy demo script that fabricated users, paid orders, payments, invoices, entitlements, analytics and revenue with a safe compatibility wrapper.
- Added an idempotent five-scenario seeder for AI software, advanced manufacturing, biomedicine, technology services and early-stage software companies.
- Persisted every demo as a complete real-domain chain: company, immutable profile, document ingestion status, private synthetic policy/version/chunk, rule/material/benefit, scan, opportunity, four-state eligibility result, exact-span evidence, application, requirements, task, workflow/agent trace and versioned artifact.
- Added public, read-only list/detail/download endpoints that fail closed unless the scenario is published, synthetic and owned by an active demo tenant.
- Added real-time DOCX, PDF, XLSX and JSON downloads through the production artifact renderer.
- Excluded demo tenants from investor totals, activity funnel, revenue, paying-customer, LLM cost, quality and system-health metrics.
- Rebuilt `/demo` as a responsive seven-step investor walkthrough with five selectable scenarios, loading/empty/error/retry states and an always-visible truthfulness boundary.
- Added a 12-document engineering data room and 3/7/15-minute demo scripts.
- Updated the OpenAPI contract and repository documentation.

## Migration

- `20260905_0020_investor_demo.py`
- Additive and forward-compatible; existing tenant rows default to `is_demo=false`.
- Upgrade from an empty database through Phase 10 succeeded.
- Phase 10 downgrade/upgrade replay succeeded.
- `alembic check` reported no model/schema drift.

## Automated verification

- Backend lint and compile: passed.
- OpenAPI contract snapshot: current.
- Full backend suite: 52 passed.
- Backend line coverage: 77.90% (50% required).
- Phase 10 integration tests: 2 passed.
- Five deterministic eval families: 11/11 synthetic cases passed; datasets remain unreviewed and are not investor accuracy claims.
- Frontend TypeScript: passed.
- Next.js 16.3.4 production build: passed, 35 routes including `/demo`.
- Production standalone frontend artifact: generated.

## Manual browser verification

- `/demo` loaded with no blank page, error overlay or console errors.
- All five synthetic scenarios rendered.
- Seven-step navigation completed from Company Profile through Deliverable.
- Biomed scenario correctly showed `Need More Information` with missing hard-gate inputs.
- DOCX request reached the backend and returned HTTP 200; all four formats also have automated signature/content-type coverage.
- Mobile viewport 390×844 showed the DEMO badge with no horizontal overflow.

## Security audit note

No dependency manifests or lockfiles changed in this phase. The previous phase's npm and Python dependency audits passed. A repeated live advisory lookup was blocked by the execution environment's outbound metadata privacy control; it was not bypassed.

## Truthfulness guarantees

- Demo cases create no fake customer identities or commercial/analytics/evaluation records.
- Every demo company and policy is labelled DEMO/synthetic.
- Synthetic policy URLs use the reserved `.invalid` domain.
- Data-room documents distinguish Implemented, Partial and Planned capabilities.
- No customer, revenue, government, funding, accuracy, SLA or certification claim was added.
