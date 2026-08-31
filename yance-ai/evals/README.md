# yance.ai AI Evals

`golden_cases/` stores versioned, human-reviewed cases. The runner currently checks deterministic
output contracts and is intentionally provider-neutral. Add semantic or judge-model metrics only
after a labeled baseline exists.

Run locally:

```bash
python evals/run_evals.py --cases evals/golden_cases/policy_matching.jsonl
```

CI fails if any required key is missing or an expected term is absent from a supplied prediction.
Do not put customer data, secrets, or raw private documents in the golden set.

