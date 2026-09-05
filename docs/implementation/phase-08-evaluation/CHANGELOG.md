# Phase 8 — Evaluation Changelog

Date: 2026-09-05

## Outcome

Yance now executes, persists, and exposes five deterministic quality-evaluation families against
named product capabilities. Every result is tied to an immutable dataset version and checksum,
keeps execution errors in its denominator, and can be inspected from question through ground
truth, answer, dimension scores, evidence, and error type.

The bundled 11-case suite is deliberately classified as synthetic and unreviewed. Its passing
result is an engineering regression signal only; the product and investor metrics explicitly
exclude it from production-quality claims.

## Evaluation contracts and datasets

- Added strict dataset-card and case contracts for policy retrieval, eligibility, citation,
  hallucination, and document generation evaluations.
- Added version, review status, data classification, reviewer/date, customer-data, demo-data,
  target, scorer, risk-tier, and tag metadata.
- Added a fail-closed loader with size/case limits, stable SHA-256 content identity, unique-case
  validation, and immutable same-version checksum enforcement.
- Added 5 canonical synthetic datasets containing 11 cases. Legacy golden cases remain in the
  repository but are not silently mixed into the new scorecard.

## Real execution and scoring

- Policy retrieval evaluates the production lexical retrieval scorer.
- Eligibility evaluates the production deterministic rule contract and four-state decision.
- Citation evaluation verifies exact policy spans, including correct rejection of unsupported
  quotations.
- Hallucination evaluation checks evidence-bound claims and prompt-injection-style unsupported
  assertions.
- Document generation executes the Application brief renderer and validates DOCX, PDF, XLSX, and
  JSON outputs instead of checking a placeholder response.
- Scoring records Correctness, Completeness, Evidence, Citation Accuracy, Hallucination Safety,
  and Actionability with explicit applicability and rationales.
- Target exceptions become persisted zero-score error cases; they are never dropped from pass,
  latency, or cost denominators.

## Persistence, API, and Admin UI

- Added additive Evaluation Dataset, Version, Case, Run, Result, Dimension Score, Evidence, and
  Error records. Eval Runs are tenant-owned and retain target/scorer/model/prompt provenance,
  counts, latency, cost, status, and release-gate outcome.
- Added platform-admin-only endpoints to run one or all evaluation families, retrieve latest
  comparable scorecards, list runs, and inspect a complete run trace.
- Added `/admin/evals` with honest empty states, six metric cards, dimension sample sizes,
  denominator disclosure, latest-per-type comparison, and dataset provenance.
- Added `/admin/evals/[runId]` for case-level question, ground truth, model answer, scores,
  evidence, errors, cost, latency, target, scorer, version, and checksum inspection.
- Investor metric availability becomes true only when all five latest non-demo families use
  reviewed dataset versions. The bundled suite therefore leaves the quality metric unavailable.

## CLI, CI, and packaging

- Replaced schema-only eval validation with `validate` and executable `run` commands; `--no-persist`
  provides a deterministic CI gate without requiring production data.
- CI now runs the five-part evaluation gate after backend tests.
- Backend container packaging now includes the canonical evaluation datasets.

## Verification

- Canonical dataset validation: 5 datasets, 11 cases, all explicitly `unreviewed`.
- Deterministic execution: 11 requested, 11 completed, 11 passed, 0 execution errors, release gate
  passed. This is not presented as production accuracy.
- Full backend suite on a fresh PostgreSQL 18 + pgvector database: 45 passed; 75.49% total coverage
  against the 50% CI floor.
- Fresh database migrated from revision zero through `20260905_0018`.
- A populated test database with 7 Eval Runs downgraded to `20260904_0017`, upgraded back to head,
  and passed `alembic check` with no model/schema drift.
- Ruff, Python compilation, and OpenAPI contract snapshot checks passed.
- Next.js production build and TypeScript validation passed with 33 routes, including the Eval
  dashboard and dynamic run trace.
- Browser verification was completed before the final citation-evidence semantic correction. A
  final browser replay was unavailable because the local Mac was locked; API, target, test, and
  production-build validation cover the corrected path, but the final visual replay remains a
  manual follow-up.

## Intentional deferrals

- The 11 synthetic cases are too small and unreviewed for production, safety, or investor quality
  claims. Human-reviewed, adjudicated, frozen datasets and release thresholds remain required.
- Current targets are bounded component evaluations, not an end-to-end live-model benchmark.
- Learned reranking, semantic citation entailment, LLM-as-judge calibration, OCR quality,
  cross-tenant security evals, and online shadow/canary evaluation remain future work.
- Phase 9 must implement authoritative subscription, quota, invoice, retention, API-key, and
  enterprise-control behavior without inventing commercial results.
