# Yance.ai Investor Readiness Report

Report date: 2026-09-06

Release line: `feature/investor-grade-upgrade`

Scope: repository architecture, product workflow, security controls, automated verification and remaining delivery risk.

## Executive conclusion

Yance.ai is now a coherent vertical Agent SaaS foundation rather than a policy-search landing-page demo. The implemented product spine persists company context, immutable policy/profile versions, structured eligibility, exact-span evidence, application work, human review, deliverables, Agent traces, usage/commercial records, evaluations and audit history in one tenant-aware system.

The release candidate supports a truthful investor walkthrough and a tested API/worker golden journey. It is suitable for controlled investor demonstrations and PoC hardening. It is **not yet represented as enterprise GA**: hosted observability, managed disaster recovery, real reviewed evaluation sets, SSO/SAML, database RLS, staging evidence for production object storage/malware scanning and an external penetration test remain explicit P1 work.

## Current architecture

```text
Next.js 16 enterprise web application
          │ HTTPS / typed JSON client
          ▼
FastAPI API ── JWT/API key auth ── RBAC ── tenant ownership ── quotas
          │
          ├── company profiles + immutable versions + verified document intelligence
          ├── policy versions/chunks + hybrid retrieval + structured rules
          ├── opportunities + eligibility + exact-span evidence
          ├── application workspace + review + versioned artifacts
          ├── durable workflow/Agent harness + worker + retries
          └── admin + analytics + billing + evals + audit/export/deletion
          │
          ├── PostgreSQL + pgvector
          ├── object-storage abstraction
          └── Agent worker + document worker + ClamAV gate
```

The deployment topology separates frontend, API, migration job, Agent worker, document worker, malware scanner and PostgreSQL. Application containers run as non-root users. Alembic holds an additive history through revision `20260906_0021`.

## Product architecture

The primary persisted lifecycle is:

`Organization → Company → CompanyProfileVersion → Document → PolicyScan → Opportunity → EligibilityResult → Evidence → Application → Requirement/Task → ApplicationArtifact → Review/Download → Next Best Action`

This turns an answer into a workspace. The current UI includes Home, Opportunities, Companies, Applications, Agents, Documents, Knowledge, Reports, Usage, Billing, Settings and role-gated Admin experiences. Opportunity and Application views expose status, evidence, requirements, tasks, timeline/activity and deliverables instead of relying on chat history.

## Agent architecture

The core harness implements `Plan → Retrieve → Reason → Act → Verify → Retry → Finish` with:

- versioned `Agent` and `Workflow` definitions;
- Pydantic structured contracts;
- durable `WorkflowRun`, `AgentRun`, `AgentStep`, `ToolCall`, `Artifact`, `Error` and `Retry` records;
- tenant/user/workflow/run correlation;
- model, prompt version, tokens, cost, latency and status fields;
- database-backed queue claiming, leases, heartbeats, idempotency and bounded retry;
- a separate worker process and a full Admin/Agent trace view.

Policy scanning invokes distinct search, eligibility, evidence and report responsibilities under the orchestrator. Critical eligibility output is not accepted until evidence verification completes.

## RAG and structured policy architecture

Policy ingestion creates checksum-addressed immutable versions and exact character-span chunks. Retrieval combines PostgreSQL full-text ranking, pgvector similarity, metadata filters and reciprocal-rank fusion. The structured policy layer stores rules, required materials and benefits; eligibility is therefore not delegated entirely to generative text.

Evidence includes conclusion linkage, source title/URL, issuer, region, article, quote boundaries, confidence and verification state. Opportunities pin both policy and company-profile versions, so decisions can be reproduced after either source changes. A separately learned reranker is not claimed.

## Major improvements delivered

1. Completed the initial 25-area code/product/security audit and P0–P3 roadmap.
2. Closed unsafe payment, cross-tenant, artifact rendering and evidence-gate paths before product expansion.
3. Replaced disconnected page flows with a consistent enterprise workspace design system.
4. Added the persisted company-to-policy-to-application domain spine.
5. Added durable Agent execution and traceability rather than a single prompt call.
6. Added immutable policy ingestion, hybrid retrieval, structured rules and exact citations.
7. Added a complete Application Workspace with requirements, documents, tasks, comments, activity, human review, versioning and DOCX/XLSX/JSON/PDF-capable rendering paths.
8. Added source-backed Admin, analytics, investor metrics, system health, feedback and error views.
9. Added five versioned eval families with evidence/error records and truthful empty states.
10. Added subscriptions, usage/quota enforcement, invoices, API keys, feature flags, audit-chain fields, export and deletion controls.
11. Added five tenant-isolated synthetic investor scenarios and a 3–5 minute `/demo` workflow that uses persisted product entities and production renderers.
12. Added explicit API/worker and Chromium E2E gates, migration rollback/forward checks, logical restore verification, bounded latency smoke, CodeQL, SBOMs and container scanning.
13. Added production-shaped company-document intelligence: real five-format parsers, quarantine/signature/archive/malware gates, durable ingestion attempts, source-locatable chunks, evidence-bearing fact candidates, human review and published-fact provenance.

## Security posture

Implemented controls include password hashing, short-lived scoped JWTs, RBAC, tenant ownership checks, hashed API keys, process-local rate limits, upload quarantine/type/size/signature/archive checks, server-side hashes, fail-closed production malware-scanning configuration, SSRF-aware policy ingestion, replay-safe payment settlement, safe renderers, production secret validation, request correlation, no sensitive body logging, security response headers, audit records and CI dependency/secret/SAST/container scanning.

Known boundaries are disclosed in [`docs/production-readiness/RISK_ACCEPTANCE.md`](docs/production-readiness/RISK_ACCEPTANCE.md). There is no certification, external penetration-test, SSO/SAML, customer-managed key or PostgreSQL RLS claim.

## Testing and release evidence

Observed locally on 2026-09-06:

| Gate | Result | Scope caveat |
|---|---:|---|
| Backend automated suite | 67 passed | clean PostgreSQL + pgvector test environment |
| Backend line coverage | 77.80% | aggregate line coverage, not risk coverage |
| API/worker golden journey | passed twice consecutively | deterministic embedding/storage substitutes; real database and product services |
| Chromium browser stories | 2 specs | investor demo previously passed; authenticated Documents workspace passed against live local Next.js + FastAPI + PostgreSQL |
| Deterministic eval gate | 11/11 passed across 5 families | synthetic and unreviewed; **not a product accuracy claim** |
| Alembic upgrade | through `20260906_0021` | local PostgreSQL 18 + pgvector |
| One-revision downgrade/upgrade | passed | validates latest revision path, not every historical production dataset |
| Logical backup/restore | passed | restored to isolated DB; revision and key counts checked |
| Frontend TypeScript | passed | `tsc --noEmit` |

The CI workflow repeats these gates and adds locked dependency audits, secret history scanning, CodeQL security-extended analysis, container builds, SPDX JSON SBOM generation, fixed high/critical vulnerability blocking and non-root runtime checks. Repository configuration does not prove that branch protection is enabled on the remote host.

## Evaluation results

The repository contains `policy_retrieval_eval`, `eligibility_eval`, `citation_eval`, `hallucination_eval` and `document_generation_eval`. Each case records question/input, ground truth, model/target answer, scores, evidence and error type. Admin metrics use persisted completed non-demo runs and display “No evaluation data yet.” when none exist.

The current 11/11 release-gate result validates deterministic contracts against synthetic unreviewed fixtures only. It must not be used in sales or investor material as real-world model accuracy. The next quality milestone is a versioned, domain-expert-reviewed corpus sampled from permissioned real workflows.

## Performance

A bounded local health-endpoint smoke completed 100 requests at concurrency 10 with 100 successes, measured p50 4.86 ms, p95 9.75 ms and p99 11.10 ms. This is only a regression smoke for request handling; it is not a production capacity, regional latency or Agent-workflow benchmark. The CI threshold is deliberately generous at p95 750 ms to catch regressions rather than imply an SLA.

The frontend uses production Next.js builds, route-level loading/error/empty states, pagination where data volume requires it and a standalone runtime artifact. Real Core Web Vitals require production telemetry before a claim.

## Metrics available

`/admin/investor-metrics` reads directly from the database and excludes tenants marked `is_demo=true`. Available metrics include total/active users, organizations, companies, policy scans, applications, reports, Agent runs, successful/failed runs, generated documents, PoC accounts, paying customers, settled revenue, LLM cost, cost/run and conversion funnel steps.

The platform also persists product analytics events, usage meters, subscription/invoice state, model token/cost/latency, run errors/retries and audit activity. Missing data renders as zero/empty state; the system does not invent customers, revenue, accuracy, usage or government relationships.

## Technical moat

The defensibility is the compound system, not access to an LLM:

- structured, versioned company context that survives individual conversations;
- a policy corpus with source lineage, metadata, exact spans and structured rules;
- deterministic eligibility gates plus evidence verification;
- a persistent application workspace, review state and versioned deliverables;
- workflow/Agent execution history, cost and failure data;
- tenant-specific knowledge and future feedback/evaluation flywheel;
- reusable orchestration primitives that can extend to adjacent regulated vertical workflows.

ChatGPT or DeepSeek can draft an answer; they do not by themselves provide this organization-owned state, reproducible decision lineage, task execution, governance, billing/quotas and quality-control loop.

## Remaining risks

There are no known open P0 issues in the current local release checks. P1 items, role owners, dates and temporary acceptance are recorded in the risk register. The most material are:

- the production ClamAV/signature-update lifecycle and real OSS ingestion path still need staging evidence;
- scanned-PDF OCR and controlled company webpage ingestion are not yet enabled;
- reviewed real-world evaluation evidence is insufficient for accuracy claims;
- hosted OpenTelemetry, centralized retention and alert delivery are not connected;
- managed backup scheduling/cross-region recovery is unproven despite the local restore drill;
- database RLS and SSO/SAML are not implemented;
- base images are tag-based in source and must be promoted by recorded digest in production;
- no external penetration test or certification exists;
- autonomous submission-channel adapters remain behind future human approval gates.
- the complete backend suite expects a pristine test database; the dedicated golden E2E is self-cleaning, but remaining integration fixtures need per-test isolation for arbitrary repeated local runs.

## Next 90 days

### Days 0–30

- Connect CI to protected required checks and an isolated staging environment.
- Deploy hosted telemetry, dashboards, alert delivery and scheduled encrypted backups; pass two restore drills.
- Verify the five-format document pipeline with real OSS and ClamAV signature updates in staging; add OCR and controlled webpage URL ingestion as separately gated capabilities.
- Pin promoted container images and third-party actions by digest/commit.
- Add policy freshness monitoring and change detection.

### Days 31–60

- Build and review a permissioned domain-expert eval corpus; publish methodology and sample size.
- Add PostgreSQL RLS defense-in-depth and shared distributed rate limiting.
- Add SSO/SAML design/implementation for enterprise pilots.
- Run retrieval, renderer, queue and full Agent workflow capacity benchmarks.
- Conduct external security assessment and remediate findings.

### Days 61–90

- Add organization-specific retrieval collections and feedback-driven eval sampling.
- Add source connectors and monitored ingestion SLAs.
- Introduce submission-channel adapters behind explicit human approval and audit gates.
- Validate scaling policies for API, worker, retrieval and rendering workloads.
- Reassess enterprise GA against SLO evidence, security assessment and reviewed quality results.

## What investors should understand about the technology

Yance is building an evidence-first execution system for professional policy workflows. Its near-term advantage is not a proprietary foundation model; it is the controlled transformation of fragmented company information and policy sources into reproducible eligibility decisions, tracked work and governed deliverables. The architecture makes that workflow measurable and extensible while keeping unsupported claims visible as missing information.

The credible financing thesis is therefore: deepen proprietary workflow/data/eval accumulation in one high-value vertical, prove repeatable delivery and unit economics, then reuse the harness, evidence model and enterprise controls for adjacent vertical Agents. The current repository demonstrates that foundation; the risk register states what must still be proven in production.
