# Security

Status: **Implemented baseline; Partial enterprise assurance**.

## Implemented controls

- Production startup rejects default JWT, bootstrap, provisioning and API-key secrets: [`yance-ai/app/core/config.py`](../../yance-ai/app/core/config.py).
- Password hashing, scoped JWT authentication and role checks: [`yance-ai/app/core/security.py`](../../yance-ai/app/core/security.py) and [`yance-ai/app/api/deps.py`](../../yance-ai/app/api/deps.py).
- Tenant-scoped queries and ownership checks across domain APIs; focused adversarial tests: [`yance-ai/tests/test_security.py`](../../yance-ai/tests/test_security.py).
- File-size/type controls and object-key isolation: [`yance-ai/app/api/routes/documents.py`](../../yance-ai/app/api/routes/documents.py).
- SSRF-aware URL ingestion controls: [`yance-ai/app/services/policies/ingestion.py`](../../yance-ai/app/services/policies/ingestion.py).
- Hashed API keys, audit log chain fields, export and deletion workflows: [`yance-ai/app/services/enterprise/`](../../yance-ai/app/services/enterprise/).
- CI dependency and secret scanning: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).
- Disclosure policy and operational guidance: [`SECURITY.md`](../../SECURITY.md) and [`yance-ai/docs/architecture/SECURITY_RUNBOOK.md`](../../yance-ai/docs/architecture/SECURITY_RUNBOOK.md).

## Known boundaries

- **Partial:** no external penetration-test report, SOC 2/ISO certification, SSO/SAML, or customer-managed encryption-key claim.
- **Partial:** rate limiting is process-local and should move to a shared distributed control before horizontal API scaling.
- **Planned:** formal threat-model review per release, external assessment, and evidence collection for a compliance program.
