# Agent Architecture

Status: **Implemented core harness; Partial worker catalogue**.

The execution model is `Plan → Retrieve → Reason → Act → Verify → Retry → Finish`, rather than a single prompt-to-answer call.

## Implemented controls

- Structured Pydantic inputs and outputs: [`yance-ai/app/services/agents/contracts.py`](../../yance-ai/app/services/agents/contracts.py).
- Versioned Agent and Workflow definitions: [`yance-ai/app/services/agents/definitions.py`](../../yance-ai/app/services/agents/definitions.py).
- Durable `WorkflowRun`, `AgentRun`, `AgentStep`, `ToolCall`, `Artifact`, `Error`, and `Retry` records: [`yance-ai/app/models/models.py`](../../yance-ai/app/models/models.py).
- Leases, heartbeats, idempotency and bounded retries: [`yance-ai/app/services/agents/harness.py`](../../yance-ai/app/services/agents/harness.py).
- Separate worker process: [`yance-ai/app/workers/agent_worker.py`](../../yance-ai/app/workers/agent_worker.py).
- Full trace UI: [`website/app/agents/`](../../website/app/agents/).

## Verification boundary

Policy decisions are pinned to a company profile version and policy version. Evidence records store exact character spans and verification state. Demo traces use the same execution entities while recording zero tokens/cost and a deterministic model name; demo runs are excluded from investor metrics.

## Partial / planned

- **Partial:** current production workers cover policy scanning and application operations; additional specialized worker behavior will be introduced behind versioned contracts.
- **Planned:** queue broker and autoscaling policy beyond database-backed claiming.
- **Planned:** model-based verifier only after golden-set evidence proves benefit over deterministic checks.
