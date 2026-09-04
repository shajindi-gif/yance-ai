# Phase 4 Changelog — Agent Harness

## Outcome

Policy scans no longer depend on FastAPI process-local background work. A scan now creates a
tenant-owned WorkflowRun and queued AgentRun, and a separate worker claims it with a database lease,
executes six structured stages, verifies invariants, writes a versioned Artifact and only then marks
the scan complete.

## Backend and data model

- Added versioned `Agent` and `Workflow` definitions with JSON input/output contracts.
- Added tenant-owned `WorkflowRun`, expanded `AgentRun`, and added `AgentStep`, `ToolCall`,
  `AgentRunError`, `AgentRetry` and `Artifact`.
- Added lease owner, expiry, heartbeat, bounded retry, next-attempt, prompt version, token, cost and
  latency fields to AgentRun.
- Added additive migration `20260903_0014_agent_harness`; existing task and deliverable records remain
  compatible. The optional WorkflowRun task identifier is indexed without a reverse foreign key to
  avoid a `PolicyScan → WorkflowRun → Task → PolicyScan` DDL cycle.
- Seeded nine versioned Agent definitions. Only Orchestrator, Policy Search, Report and QA are active;
  the other specialist Agents remain explicitly inactive until their workflows are implemented.
- Added configurable worker polling, lease duration and retry budget in environment settings.

## Execution and reliability

- Added PostgreSQL `FOR UPDATE SKIP LOCKED` claiming so multiple workers cannot execute the same run.
- Added expired-lease recovery with persisted retry records and terminal fail-closed behavior.
- Added `plan → retrieve → reason → act → verify → finish` execution with Pydantic contracts.
- Kept queue/lease/retry primitives in the Harness and isolated policy-scan business execution in a
  dedicated workflow executor so future workflows do not accumulate in one runtime module.
- Persisted policy matching and report rendering as structured ToolCalls.
- Added an explicit verifier for pinned profile provenance, scan/tenant provenance, uniqueness,
  policy snapshot presence and the four allowed eligibility states.
- Failure handling now closes the active step and open tool calls, stores only a safe message and
  exception type, and updates WorkflowRun, PolicyScan and Task consistently.
- Added separate worker services to development and production Compose definitions.

## API and product

- Added tenant-scoped `GET /agents`, `GET /agent-runs` and `GET /agent-runs/{run_id}` APIs.
- Agent registry metrics are calculated from distinct runs in AgentStep participation, so specialist
  Worker activity is represented without inventing runs or performance data.
- Added `/agents` and `/agents/[runId]` workspace pages with registry status, real metrics, six-stage
  execution trace, verification output, tool calls, artifacts, safe errors and empty states.
- Added recent Agent Runs to Home and linked task run summaries to their trace identifiers.
- Updated the deterministic OpenAPI contract snapshot.

## Verification

- PostgreSQL 18 + pgvector-compatible migration: empty database to head passed.
- Alembic ORM drift check: no new upgrade operations detected and no unresolved table-cycle warning.
- Backend tests: `31 passed`.
- Coverage gate: `68.36%` total with required minimum `60%`; Agent API `99%`, harness and policy
  scan executor `89%`.
- Ruff and Python compile checks: passed.
- Next.js 16.3.4 production build and TypeScript checks: passed; `/agents` and
  `/agents/[runId]` emitted successfully.
- Development and production Compose configuration parsing: passed (production checked without
  resolving the intentionally absent local `.env.prod`).
- Browser smoke: authenticated dashboard, Agent registry and one completed run trace verified at
  mobile and 1440×1000 desktop viewports; no browser console warnings or errors.

## Test coverage added

- API-created scans remain queued until the worker claims them.
- One execution produces six ordered completed steps, two ToolCalls and one report Artifact.
- Agent metrics include participating specialist Workers and do not manufacture cost or token usage.
- Cross-tenant Agent Run detail access returns 404.
- Expired leases are reclaimed and recorded.
- Execution errors retry twice, then fail AgentRun, WorkflowRun, PolicyScan and Task together.
- Stored failure details exclude the underlying exception message.

## Intentional deferrals

- Phase 5 will replace safe `NEED_MORE_INFORMATION` defaults with structured rule evaluation,
  evidence records, citation verification and hybrid retrieval.
- Phase 6 will add application drafting, human review and DOCX/PDF/XLSX/JSON version workflows.
- Phase 8 will add benchmark datasets and Evaluation persistence/dashboarding.
- Deterministic tools report zero tokens and zero model cost. No synthetic LLM usage is shown.
