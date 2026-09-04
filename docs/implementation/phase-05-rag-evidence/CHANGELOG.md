# Phase 5 — RAG + Evidence Changelog

Date: 2026-09-04

## Outcome

Policy scans now produce a durable, evidence-first eligibility record instead of treating a relevance score as an eligibility conclusion. Every matched opportunity pins both the published company profile version and the immutable policy version used by the scan.

The automatic engine remains deliberately fail-closed:

- a failed verified hard gate becomes `NOT_ELIGIBLE`;
- missing company facts, typed rules, or exact source text becomes `NEED_MORE_INFORMATION`;
- all machine-checked rules passing becomes `POTENTIALLY_ELIGIBLE`;
- the system never emits final `ELIGIBLE` without a future human-review transition.

## Data and migration

- Added immutable `policy_versions` with SHA-256 checksums and source metadata.
- Added exact-span `policy_chunks` with optional 1,024-dimension embeddings.
- Added typed `eligibility_rules`, `required_materials`, and `policy_benefits`.
- Added tenant-owned `eligibility_results` and `evidence` records.
- Added `opportunities.policy_version_id` so an existing decision cannot drift when a policy changes later.
- Backfilled existing policy text into real version-1 source snapshots. Backfilled chunks are explicitly marked as not embedded; no vectors or evidence were fabricated.
- Kept the legacy `policy_rules` table and API for compatibility, but it is not silently executed by the new engine.

## Retrieval and policy ingestion

- Centralized policy create/update ingestion into clean, version, chunk, embed, and metadata steps.
- Batch-embeds the full policy and all chunks in one provider request.
- Added tenant-aware paragraph retrieval using lexical ranking, vector ranking, metadata/status filters, and deterministic reciprocal-rank fusion.
- Kept whole-document vector retrieval only as a compatibility fallback for non-migrated records.
- Stored retrieval mode, policy version, and contributing chunk IDs with each opportunity.

This phase does not claim BM25 or a learned reranker. The lexical component is deterministic term/character relevance; naming it otherwise would overstate the implementation.

## Eligibility, evidence, and workflow

- Added deterministic typed operators: `eq`, `in`, `contains`, `gte`, `lte`, and `exists`.
- Added numeric-boundary-safe quote verification so a source containing `140%` cannot substantiate a `40%` claim.
- Persisted exact citation text, global character offsets, policy chunk, source URL, issuer, article, confidence, and verifier.
- Added `EligibilityAgent` and `EvidenceAgent` execution to the durable policy-scan harness.
- Registered the evidence-first scan as immutable workflow version `v2`; historical `v1` runs remain linked to their original definition.
- Added verification gates for profile provenance, policy-version provenance, structured results, valid four-state decisions, and verified evidence for positive decisions.
- Application creation now prefers source-backed structured material requirements and preserves their provenance. Keyword-derived materials remain visibly marked as unverified candidates.

## API and UI

- Policy creation and updates now create immutable source versions and retrieval chunks.
- Added controlled authoring endpoints for typed eligibility rules, required materials, and benefits. Only tenant-owned policies can be authored through these endpoints, and cited text must exist in an indexed source passage.
- Opportunity detail now returns the structured decision, criteria, missing information, evidence, materials, and benefits.
- Opportunity UI now displays the four-state result, criterion-level facts and hard gates, exact verified quotations, source links, confidence, and honest empty states.
- Removed stale UI copy describing policy scans as process-local.
- Refreshed the checked-in OpenAPI document.

## Verification

- Fresh PostgreSQL database migrated from revision zero through `20260903_0015`.
- Phase 5 migration successfully downgraded to `20260903_0014` and upgraded back to head on the disposable verification database.
- `alembic check`: no pending model changes.
- Backend tests: 36 passed on a freshly migrated PostgreSQL database with `APP_ENV=test`.
- Backend Ruff and Python compilation: passed.
- Frontend Next.js 16.3.4 production build and TypeScript checks: passed; 30 routes generated.
- Browser verification: authenticated opportunity detail rendered the persisted result, passing hard gate, exact evidence quote, source metadata, candidate-material disclaimer, and responsive workspace shell. Browser console had no warnings or errors and the page had no horizontal overflow.

## Intentional deferrals

- Arbitrary PDF, DOCX, XLSX, CSV, TXT, and URL parsing into the company knowledge base is not complete. Existing uploads still truthfully remain in their recorded ingestion state.
- A learned reranker, document OCR, policy-change re-evaluation, and human approval workflow remain later work.
- Benchmark accuracy, citation accuracy, and hallucination rates are not claimed here. Phase 8 must run the actual engine against a reviewed dataset and show `No evaluation data yet.` until results exist.
- This phase does not make payment, billing, or customer-traction claims.
