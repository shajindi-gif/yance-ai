# Evaluation

Status: **Implemented deterministic harness; real results depend on persisted reviewed runs**.

Five evaluation families are versioned under [`yance-ai/evals/datasets/`](../../yance-ai/evals/datasets/): policy retrieval, eligibility, citation, hallucination and document generation.

## Implemented

- Dataset manifests, immutable content hashes, review status and data classification: [`yance-ai/app/services/evaluations/loader.py`](../../yance-ai/app/services/evaluations/loader.py).
- Structured case contracts and six dimensions: correctness, completeness, evidence, citation accuracy, hallucination and actionability: [`yance-ai/app/services/evaluations/contracts.py`](../../yance-ai/app/services/evaluations/contracts.py).
- Deterministic scorers and release gates: [`yance-ai/app/services/evaluations/scorers.py`](../../yance-ai/app/services/evaluations/scorers.py).
- Persisted run/case/score/evidence/error records and admin dashboard: [`yance-ai/app/api/routes/admin_evals.py`](../../yance-ai/app/api/routes/admin_evals.py) and [`website/app/admin/evals/`](../../website/app/admin/evals/).
- CI executes the five-part non-persisted gate: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

The admin dashboard displays “No evaluation data yet.” when no reviewed, non-demo results exist. Synthetic runs cannot establish an investor-facing accuracy claim. Current metrics must be read from the database at diligence time; this document intentionally contains no fabricated percentage.
