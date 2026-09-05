# Service Objectives and Alert Policy

Status: **release-candidate targets; not a historical SLA claim**. These objectives become externally reportable only after a production observation window exists.

## Service indicators

| Indicator | Release-candidate objective | Measurement source |
|---|---:|---|
| API availability | 99.5% per calendar month | edge/load-balancer successful requests, excluding planned maintenance |
| Interactive API latency | p95 < 750 ms over 15 minutes | structured `request_completed.duration_ms`, excluding exports and Agent workflows |
| Server error rate | < 1% over 15 minutes | HTTP 5xx / all completed API requests |
| Agent queue start | 95% start within 60 seconds | `AgentRun.started_at - queued_at` |
| Policy scan completion | 95% finish within 10 minutes | `AgentRun.finished_at - queued_at` for policy scans |
| Agent terminal success | >= 95% over 24 hours | completed / terminal runs, segmented by workflow and version |
| Evidence verification | 100% of displayed critical eligibility conclusions | persisted verified Evidence attached to the EligibilityResult |
| Recovery point | provisional RPO <= 24 hours | successful scheduled backup timestamp |
| Recovery time | provisional RTO <= 4 hours | timed restore drill; not yet proven in managed production |

The local Phase 11 health-endpoint smoke is an engineering check only. It is not evidence for availability, capacity, or an SLA.

## Alerts

| Severity | Trigger | Owner role | Response |
|---|---|---|---|
| SEV-1 | confirmed cross-tenant access, secret exposure, payment double-settlement, total outage > 10 min | Incident Commander + Security Lead | page immediately; contain writes; follow incident runbook |
| SEV-2 | 5xx > 5% for 10 min, oldest runnable Agent job > 10 min, DB unavailable, restore/backup failure | On-call Engineer | acknowledge in 15 min; mitigate in 60 min |
| SEV-3 | p95 > 750 ms for 30 min, Agent success < 95% for 24 h, cost/run exceeds workflow budget by 20% | Service Owner | triage next business day |
| Security | critical dependency/container/SAST finding | Security Lead | block release until fixed or explicitly accepted |

## Required dimensions

Operational metrics must be filterable by environment, route template, status, workflow key/version, agent key/version, model/provider and non-sensitive tenant identifier. Raw request bodies, document text, prompts, tokens, passwords, API keys and policy source credentials must not be included in logs or alert payloads.

## Release criteria

- `/health` proves process liveness; `/health/ready` proves database readiness.
- A missing telemetry backend is a release blocker for enterprise GA, not for a local investor demo.
- Alert delivery must be exercised in staging before production cutover.
- SLO dashboards must exclude synthetic demo tenants from business-quality and investor metrics.
