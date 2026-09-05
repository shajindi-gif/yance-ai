# Observability

Status: **Implemented structured trace foundation; Partial external operations**.

## Implemented

- Structured JSON logging and context variables: [`yance-ai/app/core/logging.py`](../../yance-ai/app/core/logging.py).
- Each HTTP response carries `X-Request-ID`; request latency and status are logged without body content: [`yance-ai/app/main.py`](../../yance-ai/app/main.py).
- API responses add no-sniff, frame denial, referrer, permissions and API no-store controls; production adds HSTS.
- Agent/workflow trace records include tenant, run, model, token, cost, latency, tool calls, errors and retries: [`yance-ai/app/models/models.py`](../../yance-ai/app/models/models.py).
- Admin views expose runs, costs, errors and system-health snapshots: [`yance-ai/app/services/admin/metrics.py`](../../yance-ai/app/services/admin/metrics.py).
- Audit records store request/result/reason plus tamper-evident chain fields: [`yance-ai/app/services/enterprise/audit.py`](../../yance-ai/app/services/enterprise/audit.py).

## Partial / planned

- **Partial:** error-tracking and API-latency history are abstractions/log outputs, not a repository-backed hosted dashboard.
- **Specified:** alert thresholds, response ownership and provisional SLO/RPO/RTO are defined in [`docs/production-readiness/SLO_AND_ALERTS.md`](../production-readiness/SLO_AND_ALERTS.md).
- **Planned:** OpenTelemetry export, SLO burn-rate alert delivery and centralized log retention.
- **Planned:** operational dashboards must be connected to actual hosting infrastructure before an SLA claim.
