# Phase 6 — Application Workspace Implementation Plan

## Objective

Turn the existing Application record into an auditable case workspace that connects source evidence, company documents, requirements, execution tasks, versioned generated drafts, human review, comments, activity, and downloadable deliverables.

## Current-state findings

- The persisted Application currently exposes only Overview, Requirements, and Activity.
- Company documents cannot be linked to an Application or a specific requirement.
- The workspace cannot show the Eligibility evidence already created in Phase 5.
- There is no Application-native generated document/version/review model.
- Existing task deliverables belong to the older Task flow and cannot represent a source-pinned Application draft without fabricating a completed Agent run.
- UI copy still says all requirements are keyword-derived even when Phase 5 supplied reviewed structured materials.
- There is no Application comment thread or inspectable workspace action response.

## Deliverable slice

1. Add tenant-owned Application document links, versioned generated artifacts, and comments.
2. Return linked documents, generated versions, linked tasks, evidence, comments, and readiness in the Application detail API.
3. Add evidence-bound workspace actions: Ask, Generate, Check, Fix, and Explain. These actions are deterministic and explicitly identified as such until a verified Application Agent workflow is introduced.
4. Generate a real, source-pinned application brief and save its immutable structured snapshot, checksum, method, and version.
5. Support human Approve, Reject, Edit, and Regenerate actions without mutating previous versions.
6. Export each saved version as DOCX, PDF, XLSX, or JSON from the same immutable content snapshot.
7. Prevent Application approval unless the latest generated artifact has been approved.
8. Build the enterprise workspace tabs: Overview, Requirements, Documents, Generated, Tasks, Evidence, and Activity, plus a responsive execution panel.
9. Add additive migration, API/integration tests, OpenAPI refresh, production build, browser checks, and changelog.

## Planned files

- `yance-ai/app/models/models.py`
- `yance-ai/alembic/versions/20260904_0016_application_workspace.py`
- `yance-ai/app/services/applications/artifacts.py`
- `yance-ai/app/services/applications/workspace.py`
- `yance-ai/app/api/routes/workflow.py`
- `yance-ai/app/schemas/schemas.py`
- `yance-ai/tests/test_core_workflow.py`
- `yance-ai/tests/test_application_workspace.py`
- `yance-ai/docs/openapi.json`
- `website/lib/api.ts`
- `website/app/applications/[applicationId]/page.tsx`
- `website/components/workspace/CoreWorkflow.module.css`
- `docs/investor-readiness/02_PRODUCT_AUDIT.md`
- `docs/implementation/phase-06-application-workspace/CHANGELOG.md`

## Migration and compatibility

- Migration is additive and does not remove or rewrite existing Application, Document, Task, Artifact, or Deliverable records.
- Existing Applications remain usable and truthfully show empty states until documents or generated versions are added.
- Existing `Deliverable` and `Artifact` models remain intact for historical Task and Agent runs.
- Generated files are rendered on authenticated download from an immutable structured snapshot; no public object URL is invented.

## Release gates

- Base-to-head migration, populated downgrade/upgrade, and Alembic drift check pass.
- Tenant ownership is verified for applications, linked documents, requirements, tasks, evidence, generated versions, reviews, and comments.
- Previous artifact versions cannot be overwritten by edit, fix, or regenerate actions.
- Approval is blocked without an approved latest artifact.
- DOCX/XLSX archives open successfully; PDF has a valid signature; JSON round-trips to the stored snapshot.
- Full backend suite, lint/compile, OpenAPI snapshot, Next.js build, and browser checks pass.

## Intentional boundaries

- Evidence-bound deterministic actions are not represented as LLM answers and do not claim model quality.
- This phase does not parse uploaded company files; linked files retain their real ingestion state.
- Generated briefs are working drafts, not automatically submitted government forms.
- Notifications, multi-user assignment, and a durable Application Agent run are later workflow work.
