# Phase 4 Implementation Plan — Agent Harness

## Objective

Replace the process-local `BackgroundTasks` scan runner with a database-backed execution harness
that can be claimed by a separate worker, recovered after lease expiry, retried safely, verified
before completion and inspected as a structured run trace.

The first production workflow migrated into the harness is `policy_scan_v1`. Other specialist
Agents are registered with explicit schemas and availability state, but are not presented as
operational until their owning workflow exists.

## Current-state findings

- `AgentRun` is currently a thin log row created ad hoc inside the task function. It has no workflow,
  prompt version, structured input/output, cost, retry, lease or step/tool trace.
- The scan runs through FastAPI `BackgroundTasks`; API process loss can strand a persisted scan in
  `queued` or `running`, and four production API workers have no ownership protocol.
- Matching and PDF generation are recorded as unrelated AgentRun rows, while planning, verification
  and finish are comments rather than persisted execution states.
- LLM providers share a completion interface, but structured output, model roles, fallback and cost
  policy are not represented. Phase 4 will define the harness boundary; provider completion work
  remains incremental and must not block the deterministic scan workflow.
- There is no tenant-facing run trace API or Agent operations page.

## Design

### Durable queue and ownership

- `AgentRun` is the durable queue item. Workers claim eligible rows with PostgreSQL
  `FOR UPDATE SKIP LOCKED`, set an owner and expiring lease, then execute outside the API process.
- Expired leases are reclaimable. Every reclaim/retry is persisted as AgentRetry with a safe reason.
- A run has bounded retries and `next_attempt_at`; terminal failure updates the linked WorkflowRun,
  PolicyScan and Task.
- API containers never execute Agent work. Development and production compose files run a separate
  `agent-worker` service after migrations.

### Structured execution trace

- Agent and Workflow definitions are versioned, schema-bearing platform records.
- WorkflowRun owns tenant/user/workflow input, output, status, aggregate usage and error state.
- AgentRun owns model/provider/prompt version, structured input/output, tokens, cost, latency, lease
  and retry state.
- AgentStep persists ordered `plan → retrieve → reason → act → verify → finish` states.
- ToolCall persists structured arguments/results for policy matching and report rendering without
  storing policy text, user documents or prompts in logs.
- AgentRunError and AgentRetry provide normalized failure and recovery history.
- Artifact records the formal report output and links it to the run while retaining Deliverable for
  backward compatibility.

### Verification and idempotency

- The scan verifier checks tenant/scan provenance, pinned profile version, one opportunity per
  policy, frozen policy title/source metadata and allowed eligibility state.
- A run cannot become completed until the verify step passes.
- Matching remains idempotent on `(scan_id, policy_id)` and report/artifact creation is idempotent on
  the run identity.

### APIs and product surface

- `/agents` lists definitions and real aggregate run metrics. Inactive Agents show no fabricated
  success rate.
- `/agent-runs` lists tenant runs; `/agent-runs/{id}` returns steps, tool calls, retries, safe errors
  and artifacts.
- `/agents` in the workspace displays only database-backed status and metrics, with a trace view for
  actual runs.

## Files

- `yance-ai/app/models/models.py`
- `yance-ai/alembic/versions/20260903_0014_agent_harness.py`
- `yance-ai/app/services/agents/{contracts,definitions,harness,policy_scan}.py`
- `yance-ai/app/workers/agent_worker.py`
- `yance-ai/app/api/routes/agents.py`
- `yance-ai/app/api/routes/{workflow,tasks}.py`
- `yance-ai/app/api/router.py`
- `yance-ai/docker-compose.{dev,prod}.yml`
- `yance-ai/tests/test_agent_harness.py`
- `website/lib/{api,navigation}.ts`
- `website/components/workspace/AppShell.tsx`
- `website/app/agents/**/*`
- `docs/implementation/phase-04-agent-harness/*`

## Exit gates

- Base-to-head migration and ORM drift check pass on PostgreSQL + pgvector.
- A scan API request remains queued until a worker claims it; one worker execution produces a
  verified completed WorkflowRun/AgentRun with all six ordered step types and ToolCall records.
- Lease recovery, bounded retry/final failure and cross-tenant trace denial have integration tests.
- Worker process receives graceful termination and does not log structured inputs or sensitive data.
- Backend tests, coverage gate, OpenAPI snapshot, frontend build and desktop/mobile Agent trace smoke
  pass.

## Explicit deferrals

- Phase 5 owns parsed document retrieval, Evidence records, structured policy rules and citation
  verification.
- Phase 6 owns application drafting, human review and versioned DOCX/PDF/XLSX/JSON artifacts.
- Phase 8 owns Evaluation records and quality dashboards.
- Cost remains nullable/zero for deterministic internal tools until provider-specific pricing is
  configured; no synthetic cost is inferred.
