# Phase 8 — Evidence-grounded Evaluation Implementation Plan

## Objective

Replace the schema-only eval placeholder with an executable, versioned and persisted evaluation
system for policy retrieval, eligibility, citation, hallucination safety and document generation.
Every displayed metric must come from completed case executions, retain its denominator and
dataset/target/scorer provenance, and include failed/error cases rather than silently dropping
them.

## Current-state findings

- `evals/run_evals.py` only checks four required JSON keys and never executes a retrieval,
  eligibility, evidence or document path.
- The two legacy `golden_cases` rows have no dataset card, target version, scorer version, risk
  policy, review status or persisted result. They cannot support an accuracy claim.
- No EvalDataset, EvalRun, case result, dimension score, evidence result or normalized Eval error
  exists in the database.
- Phase 7 deliberately shows `No evaluation data yet.` because there is no trustworthy source.
- Current deterministic production components provide bounded evaluation targets: lexical policy
  scoring, typed eligibility operators, exact citation spans and application artifact renderers.
  This phase will evaluate those named capabilities and will not call them a benchmark of semantic
  reranking, OCR or autonomous LLM drafting.

## Metric and denominator model

The dashboard uses the latest completed non-demo run for each selected eval type:

- Accuracy: mean applicable Correctness score.
- Citation Accuracy: mean applicable Citation Accuracy score.
- Hallucination Rate: `1 - mean applicable Hallucination Safety score`.
- Pass Rate: passed cases divided by every requested case, including execution errors.
- Average Latency: total case execution milliseconds divided by every requested case.
- Average Cost: persisted case cost divided by every requested case; deterministic targets record
  real zero cost rather than an inferred provider price.

Completeness, Evidence and Actionability remain visible diagnostic dimensions. Metrics never mix
currencies or dataset versions, and missing applicable observations render unavailable rather than
zero.

## Dataset truthfulness policy

- Canonical datasets live under `evals/datasets/<eval_type>/` with a dataset card and JSONL cases.
- The bundled Phase 8 cases are synthetic engineering fixtures with no customer data. They are
  explicitly `review_status=unreviewed` and are not eligible for investor-quality metrics.
- Human review is an external governance act. Code cannot self-promote a dataset to reviewed.
- Dataset version content is immutable: a changed manifest or case set requires a new version.
- Legacy two-row cases remain for compatibility but are excluded from the canonical runner.

## Deliverable slice

1. Add EvalDataset, EvalDatasetVersion, EvalCase, EvalRun, Evaluation,
   EvaluationDimensionScore, EvaluationEvidence and EvaluationError.
2. Add an additive migration with tenant ownership for executions/results and global immutable
   dataset definitions.
3. Define strict Pydantic contracts, dataset loader/checksums and five target adapters that execute
   named current product capabilities.
4. Add deterministic dimension scorers, case-level errors and release thresholds. Exceptions and
   timeouts stay in the denominator.
5. Replace the CLI with `validate` and executable `run --no-persist` release-gate modes.
6. Add platform-admin APIs to execute one/all datasets, list runs, aggregate the latest comparable
   runs and inspect Question, Ground Truth, Model Answer, Score, Evidence and Error Type.
7. Replace the Admin Eval placeholder with persisted resource rows and add `/admin/evals` plus
   `/admin/evals/[runId]`.
8. Make Phase 7 evaluation availability dynamic but keep investor eligibility false until a
   completed run uses a human-reviewed non-demo dataset.
9. Add tests for immutable versions, five real target executions, error denominators, platform
   permissions, aggregation definitions, empty state and safe drill-down payloads.
10. Add the executable eval gate to CI and copy datasets into the backend runtime image.

## Planned files

- `yance-ai/app/models/models.py`
- `yance-ai/alembic/versions/20260905_0018_evaluation.py`
- `yance-ai/app/schemas/schemas.py`
- `yance-ai/app/api/router.py`
- `yance-ai/app/api/routes/admin.py`
- `yance-ai/app/api/routes/admin_evals.py`
- `yance-ai/app/services/admin/metrics.py`
- `yance-ai/app/services/evaluations/{contracts,loader,targets,scorers,runner,metrics}.py`
- `yance-ai/evals/README.md`
- `yance-ai/evals/run_evals.py`
- `yance-ai/evals/datasets/**/*`
- `yance-ai/Dockerfile`
- `.github/workflows/ci.yml`
- `yance-ai/docs/openapi.json`
- `yance-ai/tests/test_evaluations.py`
- `website/lib/api.ts`
- `website/app/admin/page.tsx`
- `website/app/admin/evals/page.tsx`
- `website/app/admin/evals/[runId]/page.tsx`
- `website/components/workspace/AdminDashboard.module.css`
- `docs/investor-readiness/{02_PRODUCT_AUDIT,05_AGENT_RAG_AUDIT}.md`
- `docs/implementation/phase-08-evaluation/CHANGELOG.md`

## Compatibility and migration

- Migration is additive and does not rewrite Agent, policy, Application or analytics records.
- Eval Runs may optionally reference an AgentRun, but offline evaluation remains separate from
  production task completion.
- The Phase 7 Admin resource name `evals` remains stable and begins returning persisted Eval Runs.
- Existing databases and users receive no seeded results; the dashboard remains empty until an
  authorized run actually executes.

## Release gates

- All five dataset types validate and execute through the same target/scorer registry used by the
  persistence service.
- Requested cases equal completed plus errored cases; no failure is excluded from pass-rate or
  latency/cost denominators.
- Dataset checksum mismatch at the same version fails closed.
- Tenant Owner/Admin receives 403; only explicit platform administrators can create or inspect
  cross-tenant Eval Runs.
- Empty databases show `No evaluation data yet.` and never show 0%/100% cards.
- Dashboard metrics reconcile exactly to stored dimension/result rows and identify dataset,
  version, target, scorer, risk, review status, sample size and errors.
- Base-to-head migration, populated downgrade/upgrade, Alembic drift, full backend tests with
  coverage floor, executable eval CLI gate, OpenAPI snapshot, Next.js build and browser checks pass.

## Intentional boundaries

- The bundled regression set is small, synthetic and unreviewed. Passing it is a software release
  signal, not a claim about production accuracy or customer outcomes.
- Hybrid vector recall, learned reranking, OCR, semantic claim entailment and LLM document quality
  need larger reviewed datasets and their owning production capabilities.
- Judge-model scoring is not enabled until a human-labelled calibration set exists.
- Production customer material is never copied into the repository or default evaluation store.
