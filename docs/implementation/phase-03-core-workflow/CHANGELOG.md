# Phase 3 Changelog — Core Product Workflow

## Outcome

Yance now has a persisted, tenant-scoped business workflow from registration through an Application
workspace. This phase deliberately establishes the non-AI system of record first; capabilities that
require durable Agent execution, parsed evidence, verified eligibility or generated application
documents remain visibly unavailable until their owning phases.

## Delivered

- Registration and tenant provisioning create an explicit Membership alongside the existing User
  tenant binding.
- Every Company receives a structured CompanyProfile draft. Publishing creates immutable numbered
  CompanyProfileVersion snapshots and asserted CompanyFact records.
- Document transport and ingestion state are separate. A successful signed upload becomes
  `status=uploaded` and `ingestion_status=pending`, never “parsed” by implication.
- PolicyScan persists request identity, requesting user, pinned profile version, status, Task and
  opportunity count. Idempotency keys are database-unique and concurrent duplicate commits recover
  the winning record.
- Opportunity freezes the policy metadata used during matching, separates relatedness score from
  four-state eligibility, and is unique per scan and policy.
- Eligibility remains `NEED_MORE_INFORMATION` until the evidence-first engine is delivered.
- Application validates tenant and Company/Opportunity provenance, creates persisted candidate
  requirements and activity history, and enforces explicit status transitions.
- Generic Task creation fails closed for unsupported professional outcomes. It cannot emit a normal
  policy report while claiming to be a deep diagnosis or application draft.
- Workspace routes now cover Companies, profile versions, Documents, Opportunities, opportunity
  detail, Applications and Application detail. Dashboard metrics and Next Best Action derive only
  from tenant-scoped server records.
- React development-mode request races no longer allow a disposed page load to overwrite current
  workspace state with a stale error.
- The checked-in OpenAPI contract is deterministic and CI rejects unreviewed contract drift.

## Database migration

`20260903_0013_core_workflow` is additive. It creates Membership, CompanyProfile,
CompanyProfileVersion, CompanyFact, PolicyScan, ApplicationRequirement and ApplicationActivity;
adds lifecycle/snapshot references to existing tables; backfills membership and initial profile
drafts; and retains all legacy columns and records.

## Verification evidence

- PostgreSQL 18 + pgvector base-to-head migration: passed.
- `alembic check`: passed with no model/migration drift.
- Backend Ruff and bytecode compilation: passed.
- Backend suite: 29 passed; application coverage 63.56% against a 60% local gate.
- Core integration test covers registration, membership, profile completion/versioning, upload
  lifecycle, unpublished-scan rejection, scan idempotency, opportunity uniqueness/snapshot,
  application provenance, requirement updates, allowed/forbidden status transitions and
  cross-tenant denial.
- OpenAPI snapshot check: passed.
- Next.js production build and TypeScript check: passed; 29 static-generation entries completed.
- Browser smoke against a real temporary database: login plus Dashboard, Companies/Profile,
  Documents, Opportunities/Detail and Applications/Workspace all loaded without console errors or
  framework error overlays.
- Responsive smoke at 390 × 844: Dashboard and Application workspace had no horizontal overflow.

## Explicit deferrals and release gates

- The scan runner is still process-local and cannot recover from process loss. Phase 4 must replace
  it with the durable Agent Harness, leases/retries and full run/step/tool trace.
- Uploaded objects are not parsed, cleaned, chunked or embedded. URL ingestion is intentionally not
  exposed before the Phase 5 SSRF-safe worker exists.
- Candidate material gaps are keyword-derived, marked unverified and never classified as hard gates.
- Eligibility evidence, policy clause citations, confidence calibration and verifier output are not
  yet persisted; the safe state is `NEED_MORE_INFORMATION`.
- Application Generated/Documents/Tasks/Evidence tabs, Human Review actions, DOCX export and the AI
  Agent side panel require Phases 4–6.
- Membership is a compatibility layer, not yet a multi-organization session switcher. Current auth
  continues to bind one User to one tenant until the enterprise tenancy phase.
- Browser verification used clearly named integration-test records in a temporary local database;
  no customer, revenue, accuracy or growth data was created or asserted.
