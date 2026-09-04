# Phase 6 — Application Workspace Changelog

Date: 2026-09-04

## Outcome

An Application is now an auditable execution workspace rather than a status record. It connects
the company, frozen opportunity and eligibility decision, exact policy evidence, required
materials, uploaded company documents, a real execution task, versioned generated drafts,
comments, activity, and human review in one tenant-scoped surface.

The current workspace actions are explicitly identified as `deterministic-evidence-v1`. They use
persisted decisions and source snapshots and are not represented as LLM output or autonomous
government-form submission.

## Data and migration

- Added tenant-owned `application_document_links`, `application_artifacts`, and
  `application_comments` tables in additive migration `20260904_0016`.
- Application document links can optionally satisfy a specific requirement and are idempotent for
  the same Application, document, and requirement.
- Application artifacts retain immutable structured content, a frozen source snapshot, generation
  method, SHA-256 checksum, version, reviewer identity, review time, and review note.
- Artifact versions are allocated while locking the Application row, preventing concurrent version
  collisions.
- Existing Application, Document, Task, legacy Artifact, and Deliverable records were not removed
  or rewritten.

## Workflow and API

- Application creation now creates a persisted material-preparation/review Task without inventing
  an Agent Run.
- Application detail now returns readiness, exact evidence, linked documents with their real upload
  and ingestion states, generated versions, tasks, comments, and activity.
- Readiness blocks review when a hard requirement is missing, eligibility is unsafe, or a positive
  decision has no verified evidence.
- Application approval requires an Owner/Admin and an approved latest artifact.
- Approve, reject, edit, regenerate, and fix actions preserve prior versions. Only the latest
  version can be edited or reviewed, and Fix requires a rejected latest version in
  `revision_requested` state.
- Approved, submitted, completed, review, and cancelled projects reject further artifact writes;
  existing approved outputs remain downloadable.
- Ask and Explain return only persisted eligibility text and citations. Check evaluates the stored
  readiness rules. Generate and Fix create real source-pinned artifacts and server-owned
  `document_generated` events.
- Authenticated exports render DOCX, PDF, XLSX, and JSON from the same saved content snapshot.

## Product surface

- Replaced the minimal Application page with Overview, Requirements, Documents, Generated, Tasks,
  Evidence, and Activity tabs.
- Added a responsive evidence-bound execution panel with Ask, Generate, Check, Fix, and Explain.
- Added document-to-requirement association, human comments, requirement state controls, artifact
  review controls, immutable version history, and four-format download actions.
- Empty and pending states state what is actually persisted; an uploaded document is not described
  as parsed until ingestion says so.

## Verification

- PostgreSQL 18 + pgvector database migrated from revision zero through `20260904_0016`.
- The Phase 6 migration downgraded to `20260903_0015`, upgraded to head on populated test data, and
  passed `alembic check` with no model/schema drift.
- Full backend suite on a freshly migrated database: 40 passed; total coverage 72.54% against the
  enforced 50% CI floor.
- Renderer tests opened the generated DOCX and XLSX archives, round-tripped JSON, checked the PDF
  signature, and verified XML escaping/control-character removal.
- Backend Ruff and Python compilation: passed.
- Next.js 16.3.4 production build and TypeScript validation: passed; 30 routes generated.
- Browser verification against the real API/database covered login, the complete workspace,
  version history, linked document, evidence, task, comments, activity, and a persisted Check
  action. No browser console warnings/errors or horizontal overflow were found.

## Intentional deferrals

- Uploaded company documents are not yet parsed, OCR'd, chunked, or used as company evidence.
- The Application execution panel does not yet dispatch a durable Application Agent run; its
  deterministic engine name is shown to users to avoid overstating automation.
- Generated files are structured application briefs, not official authority-specific templates,
  e-signatures, or automatic submissions.
- Multi-user assignment, notifications, official template mapping, and external submission
  integrations remain future workflow work.
- No accuracy, completion-time, cost, customer, or revenue metric is asserted by this phase.
