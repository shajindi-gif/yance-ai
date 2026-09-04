# Phase 5 — RAG + Evidence Implementation Plan

## Objective

Turn policy matching into an evidence-first decision pipeline without weakening the existing fail-closed eligibility boundary. A relevance match is not an eligibility decision.

## Current-state findings

- Policies are retrieved as whole documents through one 1,024-dimension vector.
- Policy text is mutable and has no immutable source version or checksum.
- `PolicyRule.rule_json` is untyped and tenant-owned; it is not safe to execute as a decision rule.
- Opportunities persist a score explanation, but no criterion-level eligibility result or source citation.
- The independent LLM policy evaluator is not connected to the workflow and is below the release gate recorded in the audit.
- The opportunity UI has no inspectable evidence trail.

## Deliverable slice

1. Add immutable `PolicyVersion` and paragraph-level `PolicyChunk` records with source metadata, offsets, checksums, and optional embeddings.
2. Add typed `EligibilityRule`, `RequiredMaterial`, and `PolicyBenefit` records bound to a policy version.
3. Add tenant-owned `EligibilityResult` and `Evidence` decision records bound to an opportunity and pinned company profile version.
4. Centralize policy ingestion so create/update operations version and chunk source content.
5. Add lexical + vector hybrid chunk retrieval with metadata/tenant visibility filters and deterministic reciprocal-rank fusion.
6. Add a deterministic eligibility engine. Missing facts, rules, or exact source quotes produce `NEED_MORE_INFORMATION`; failed hard gates produce `NOT_ELIGIBLE`; verified hard gates can produce only `POTENTIALLY_ELIGIBLE`. `ELIGIBLE` remains a human-reviewed state.
7. Run Eligibility and Evidence workers inside the existing Plan → Retrieve → Reason → Act → Verify → Finish harness.
8. Expose criterion, citation, material, and benefit data on the opportunity detail API and UI.
9. Add migration, integration/unit tests, OpenAPI refresh, build verification, and manual browser verification.

## Files

- `yance-ai/app/models/models.py`
- `yance-ai/alembic/versions/20260903_0015_rag_evidence.py`
- `yance-ai/app/services/policies/ingestion.py`
- `yance-ai/app/services/policies/retrieval.py`
- `yance-ai/app/services/policies/eligibility.py`
- `yance-ai/app/services/report/matcher.py`
- `yance-ai/app/services/agents/policy_scan.py`
- `yance-ai/app/services/agents/contracts.py`
- `yance-ai/app/services/agents/definitions.py`
- `yance-ai/app/services/agents/harness.py`
- `yance-ai/app/api/routes/policies.py`
- `yance-ai/app/api/routes/workflow.py`
- `yance-ai/app/schemas/schemas.py`
- `yance-ai/tests/test_rag_evidence.py`
- `yance-ai/tests/test_core_workflow.py`
- `website/lib/api.ts`
- `website/app/opportunities/[opportunityId]/page.tsx`
- `website/components/workspace/CoreWorkflow.module.css`
- `yance-ai/docs/openapi.json`
- `docs/investor-readiness/05_AGENT_RAG_AUDIT.md`
- `docs/implementation/phase-05-rag-evidence/CHANGELOG.md`

## Migration and compatibility

- Migration is additive; no existing policy, opportunity, or legacy rule is deleted.
- Existing policies are backfilled into version 1 using their real stored content and source metadata.
- Backfilled chunks intentionally have no fabricated embeddings. They remain available to lexical retrieval and exact citation validation.
- Legacy `policy_rules` remain readable but are not silently executed as typed eligibility logic.

## Release gates

- Empty database migrates to head; Alembic reports no model drift.
- Existing test suite and new evidence tests pass on PostgreSQL.
- Citation spans must round-trip exactly to immutable source text.
- Cross-tenant policy/rule/result/evidence access is rejected.
- Backend lint/compile and frontend production build pass.
- Browser checks cover empty, safe fallback, verified evidence, and mobile layouts.
