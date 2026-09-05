# Multi-tenancy

Status: **Implemented application isolation; Partial database hardening**.

## Boundary

- Tenant-owned entities carry a non-null `tenant_id` with indexed foreign keys and cascade behavior: [`yance-ai/app/models/models.py`](../../yance-ai/app/models/models.py).
- Auth principals include tenant and role, and API dependencies enforce Owner/Admin/Member/Viewer permissions: [`yance-ai/app/api/deps.py`](../../yance-ai/app/api/deps.py).
- Cross-tenant access and IDOR cases are covered by security and workflow tests: [`yance-ai/tests/test_security.py`](../../yance-ai/tests/test_security.py) and [`yance-ai/tests/test_core_workflow.py`](../../yance-ai/tests/test_core_workflow.py).
- Shared policies have `tenant_id=null`; private policies are visible only within their tenant: [`yance-ai/app/services/policies/visibility.py`](../../yance-ai/app/services/policies/visibility.py).
- Synthetic demo workspaces require `Tenant.is_demo=true`, use private policies, and are excluded from platform metrics: [`yance-ai/app/api/routes/demo.py`](../../yance-ai/app/api/routes/demo.py) and [`yance-ai/app/services/admin/metrics.py`](../../yance-ai/app/services/admin/metrics.py).

## Partial / planned

- **Partial:** isolation is enforced in application services and tests; PostgreSQL row-level security is not enabled.
- **Planned:** add RLS as defense in depth after connection-pooling/session-context design is validated.
- **Planned:** enterprise SSO, SCIM and region-specific residency controls.
