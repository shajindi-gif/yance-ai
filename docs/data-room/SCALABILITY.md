# Scalability

Status: **Architecture supports incremental scaling; load limits are not yet benchmarked**.

## Existing scaling properties

- Stateless API processes with configurable database pool: [`yance-ai/app/core/db.py`](../../yance-ai/app/core/db.py) and [`yance-ai/app/core/config.py`](../../yance-ai/app/core/config.py).
- Worker claiming uses leases, heartbeats, retry schedules and an indexed claimable state: [`yance-ai/app/services/agents/harness.py`](../../yance-ai/app/services/agents/harness.py).
- Search executes in PostgreSQL/pgvector with filters and bounded result sets: [`yance-ai/app/services/policies/retrieval.py`](../../yance-ai/app/services/policies/retrieval.py).
- Large files are represented by object-storage keys rather than database blobs: [`yance-ai/app/services/oss.py`](../../yance-ai/app/services/oss.py).
- Pagination exists for administrative collections and workspace lists.

## Bottlenecks and triggers

| Trigger | Next change | Status |
|---|---|---|
| API saturation | horizontal API replicas + shared rate limiter | Planned |
| Worker queue delay | separate worker pools by workflow and autoscale | Planned |
| Retrieval latency/corpus growth | index tuning, read replicas, then dedicated vector service only if measured | Planned |
| Artifact CPU pressure | isolate PDF/document renderer workers | Planned |
| Regional requirement | multi-zone database and region-aware object storage | Planned |

No throughput, concurrency, p95 latency or maximum-corpus claim is made until a reproducible load benchmark is checked into the repository.
