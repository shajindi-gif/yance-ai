# Incident Response

## Roles

- **Incident Commander:** owns severity, decisions, timeline and closure.
- **Operations Lead:** deployment, rollback, database and infrastructure actions.
- **Security Lead:** containment, evidence preservation and breach assessment.
- **Product/Customer Lead:** user impact, approved communications and workaround.
- **Scribe:** immutable timeline, commands, evidence and follow-ups.

One person may hold several roles in an early-stage team, but the active role must be written in the incident record.

## First 15 minutes

1. Open an incident record with start time, environment, reporter, symptoms and request/run IDs.
2. Classify severity using `SLO_AND_ALERTS.md`.
3. Preserve relevant logs and deployment identifiers; never paste secrets or customer document contents into chat.
4. Stop the harmful path with the narrowest reversible control: feature flag, worker pause, route disablement or rollback.
5. For suspected tenant isolation or credential compromise, revoke affected sessions/API keys and preserve audit records before broader changes.

## Investigation order

1. Edge and API availability, readiness and recent deployment.
2. Database health, migration revision, locks and connection saturation.
3. Agent queue depth, oldest queued run, retry/error codes and lease state.
4. LLM/provider status, budget/quota rejection and latency.
5. Object storage and document processing state.
6. Billing provider event ledger and idempotency keys for payment incidents.

Correlate using `request_id`, `run_id`, `workflow_run_id` and `tenant_id`. Do not query unrelated tenants.

## Containment and recovery

- Prefer pausing the affected worker/workflow or disabling a feature flag over shutting down the entire platform.
- Roll back application images only when the prior image is compatible with the current schema.
- Use Alembic downgrade only after reviewing the exact migration and taking a verified backup.
- Never edit settled payments, audit-chain fields or approved artifact history in place.
- Validate `/health/ready`, a non-destructive authenticated request and the affected golden path before declaring recovery.

## Communication

Only confirmed facts are communicated. State impact window, affected capability, workaround and next update time. Do not claim “no data loss” or “no breach” until evidence supports it. Legal/privacy notification decisions require the designated business and legal owner.

## Closure

Within five business days, publish a blameless review containing scope, timeline, root cause, contributing controls, recovery evidence, user impact, detection gap and dated owners. Create regression tests for every reproducible software cause.
