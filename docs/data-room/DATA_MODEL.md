# Data Model

Status: **Implemented**.

The relational model separates business truth, source snapshots, decisions, execution traces, commercial records and telemetry.

| Domain | Core entities |
|---|---|
| Identity | Tenant, User, Membership |
| Company intelligence | Company, CompanyProfile, CompanyProfileVersion, CompanyFact, Document, DocumentIngestionRun, DocumentContent, DocumentChunk, DocumentFactCandidate |
| Policy graph | Policy, PolicyVersion, PolicyChunk, EligibilityRule, RequiredMaterial, PolicyBenefit |
| Opportunity | PolicyScan, Opportunity, EligibilityResult, Evidence |
| Execution | Workflow, WorkflowRun, Agent, AgentRun, AgentStep, ToolCall, Error, Retry |
| Delivery | Application, Requirement, Task, Activity, Comment, ApplicationArtifact |
| Enterprise | Plan, Subscription, Usage, Invoice, APIKey, AuditLog, FeatureFlag, Export, DeletionRequest |
| Quality | EvalDataset, EvalDatasetVersion, EvalRun, EvalCaseResult, scores/evidence/errors |

Authoritative definitions are in [`yance-ai/app/models/models.py`](../../yance-ai/app/models/models.py); schema evolution is in [`yance-ai/alembic/versions/`](../../yance-ai/alembic/versions/).

Key lineage is explicit: a document candidate pins an exact document/excerpt/locator and reviewer; a published fact retains its source document; a scan pins a profile version; an opportunity pins a policy version; an eligibility result pins both; evidence pins an exact policy chunk; an artifact stores a source snapshot and checksum.
