# Phase 3 Implementation Plan — Core Product Workflow

## Objective

Persist the non-AI business spine of the Golden Journey without replacing the existing stack or
claiming that document parsing, durable Agent execution, evidence verification or application
generation already exists:

`Register → Tenant workspace → Company → Versioned profile → Document ingest request → Policy scan
request → Opportunity snapshot → Application workspace`

## Current-state findings

- Registration already creates a Tenant, owner User and default Company, but membership is encoded
  only on `users.tenant_id`; there is no durable Membership record.
- Company profile facts are stored in an unversioned `metadata_json` object, so later decisions
  cannot identify the exact profile state they used.
- The upload API safely registers PDF, DOCX, XLSX, CSV and TXT objects, but stops at `uploaded` and
  exposes no parse/ingestion lifecycle. URL ingestion does not exist.
- `reports/match` performs an immediate model call and inserts a new Opportunity for every policy on
  every invocation. There is no PolicyScan identity or `(scan, policy)` uniqueness boundary.
- Opportunity stores a mutable policy foreign key and score, but not the policy metadata/profile
  version used for the decision. Match score is not eligibility.
- The standalone eligibility API returns structured output but does not persist it. Evidence and
  eligibility persistence belong to Phase 5; Phase 3 must use `NEED_MORE_INFORMATION` by default.
- Application creation validates Company and Opportunity separately but does not prove that the
  Opportunity belongs to that Company. It creates no requirements or activity history.
- Existing background tasks are process-local and cannot survive a restart. Phase 3 may persist a
  scan request and reuse the current runner for compatibility, but durable leases/retries/outbox and
  the unified Agent Harness remain Phase 4 release gates.
- The frontend has no Companies, Documents, Opportunities or Application workspace routes.

## Change slices

### 1. Additive domain schema

- Add `memberships` as a compatibility layer over current Tenant/User ownership and backfill one
  active membership per existing user.
- Add stable `company_profiles`, immutable `company_profile_versions`, and typed `company_facts`.
- Add `policy_scans` and bind new opportunities to a scan and profile version.
- Add immutable policy snapshot fields and explicit eligibility status/confidence to Opportunity.
- Add `application_requirements` and `application_activities`; optionally bind Tasks to an
  Application.
- Use forward-only migration and retain existing Company metadata/Application form data.

### 2. Company profile contract

- Define a Pydantic profile schema covering identity, location, founding date, company scale,
  revenue/funding stage, certifications, IP, product, R&D, talent, projects and current needs.
- Create/update a draft profile version through tenant-scoped APIs.
- Publishing creates an immutable numbered version; later scans pin that version.
- Return completeness from real populated fields, never a fabricated score.

### 3. Document ingest request contract

- Preserve signed direct upload and tenant/company validation.
- Add explicit lifecycle fields (`source_type`, `ingestion_status`, `ingestion_error`) so upload is
  not confused with successful parsing.
- Completing an upload keeps transport status at `uploaded` and sets `ingestion_status=pending`;
  Phase 5 owns parser execution.
- Do not add a URL-fetching endpoint before SSRF-safe ingestion workers exist.

### 4. Scan and opportunity contract

- Add tenant-scoped scan create/list/detail APIs and idempotency key support.
- A scan request pins the latest published profile version, creates one policy-scan Task and emits
  authoritative `policy_scan_started`/`policy_scan_completed` events.
- Match persistence uses one Opportunity per `(scan, policy)` and freezes policy display metadata.
- Opportunity list/detail APIs return the snapshot and explicit four-state eligibility value.

### 5. Application contract

- Require Opportunity and Company to belong to the same tenant and to each other.
- Create material Requirements only from persisted opportunity gap data and record an immutable
  application-created Activity.
- Add application detail and status transition APIs with explicit allowed transitions.

### 6. Product routes

- Add `/companies`, `/companies/[id]`, `/documents`, `/opportunities`,
  `/opportunities/[id]`, and `/applications/[id]` inside the workspace shell.
- Company UI edits the typed profile; document UI performs the real signed-upload sequence and
  labels ingestion as pending; opportunity UI distinguishes match score from eligibility.
- Opportunity detail can create a real Application and route to its persisted workspace overview.
- Dashboard metrics come from tenant-scoped queries and use empty states when no records exist.

### 7. Contract and workflow tests

- Add integration coverage for registration membership/profile creation, company profile versioning,
  document lifecycle, scan idempotency/opportunity uniqueness, cross-tenant access and
  company-opportunity Application consistency.
- Export and compare an OpenAPI contract snapshot.
- Add a browser E2E for the non-AI persisted path; AI execution remains outside this phase gate.

## Files

- `yance-ai/app/models/models.py`
- `yance-ai/app/schemas/schemas.py`
- `yance-ai/app/api/routes/{auth,companies,documents,workflow,tasks}.py`
- `yance-ai/app/services/company_profiles.py`
- `yance-ai/app/services/report/matcher.py`
- `yance-ai/alembic/versions/20260903_0013_core_workflow.py`
- `yance-ai/scripts/export_openapi.py`
- `yance-ai/docs/openapi.json`
- `yance-ai/tests/test_core_workflow.py`
- `.github/workflows/ci.yml`
- `website/lib/{api,navigation}.ts`
- `website/components/workspace/*`
- `website/app/{dashboard,companies,documents,opportunities,applications}/**/*`
- `docs/implementation/phase-03-core-workflow/*`

## State and integrity rules

- Match score and eligibility are separate fields.
- New opportunities are unique per scan and policy; rescans create a new traceable snapshot rather
  than silently mutating history.
- A scan cannot run without a published CompanyProfileVersion.
- A created Application must reference an Opportunity for the same Company and tenant.
- Existing metadata, opportunities and applications remain readable after migration.
- Viewer can read but cannot create/update/publish/scan/apply.
- Server-side events are the only source for workflow completion and application creation metrics.
- Generic task creation fails closed: policy scans must use `/policy-scans`, and unsupported diagnosis
  or draft task types cannot masquerade as completed Agent work.

## Exit gates

- Base-to-head migration and `alembic check` pass against PostgreSQL + pgvector.
- Backend Ruff, compile and full tests pass without lowering the coverage floor.
- Frontend production build and type check pass.
- Register, profile version, document request, scan request, opportunity and application contract
  tests pass, including cross-tenant negative cases.
- Browser desktop/mobile smoke covers every new route with no error overlay or fake data.
- Changelog names every deferred capability and the current process-local worker limitation.

## Rollback

The migration is additive. Existing Company, Document, Opportunity, Application and Task columns
are retained. Reverting application code leaves new tables/columns unused; a later reviewed cleanup
migration may remove them only after data-retention approval.
