# yance.ai Evaluation Harness

This directory contains the canonical, versioned evaluation bundle for five capabilities:

- `policy_retrieval_eval`
- `eligibility_eval`
- `citation_eval`
- `hallucination_eval`
- `document_generation_eval`

Every dataset has a `dataset.json` card and JSONL cases. The bundled cases are synthetic engineering
fixtures, contain no customer data and are deliberately marked `review_status=unreviewed`. A pass
is a narrow software regression signal, not a production accuracy or customer-outcome claim.

Validate contracts and immutable metadata:

```bash
python evals/run_evals.py validate
```

Execute all five current target adapters without writing database metrics (the CI release gate):

```bash
python evals/run_evals.py run --no-persist
```

Persist a real run from a trusted server shell by identifying an existing platform administrator:

```bash
python evals/run_evals.py run --tenant-slug TENANT --email ADMIN@example.com
```

The Admin API/UI uses the same loader, targets, scorers and persistence service. Errors remain case
rows and stay in pass-rate, latency and cost denominators. Reusing a dataset version with different
content fails closed; create a new version instead.

`golden_cases/` is retained as a legacy compatibility fixture and is not read by the canonical
runner. It has no reviewed dataset card and must not be used to claim product quality.
