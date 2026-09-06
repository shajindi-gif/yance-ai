# System Architecture

Status: **Implemented foundation; Partial production operations**.

```text
Next.js web client
        │ HTTPS / JSON
        ▼
FastAPI API ── auth / RBAC / tenant boundary / quotas
        │
        ├── Company + Document Intelligence
        ├── Policy/RAG + Eligibility + Evidence
        ├── Application Workspace + Artifact Renderer
        ├── Agent Harness + Workflow Runs
        └── Admin + Analytics + Billing + Evals
        │
        ▼
PostgreSQL + pgvector       Object storage adapter
        │                           │
        ├──────── Agent worker ─────┤
        └──── Document worker ─ ClamAV ─ local Tesseract OCR
```

## Implemented

- Next.js App Router client and centralized API client: [`website/app/`](../../website/app/) and [`website/lib/api.ts`](../../website/lib/api.ts).
- FastAPI composition and request IDs: [`yance-ai/app/main.py`](../../yance-ai/app/main.py) and [`yance-ai/app/api/router.py`](../../yance-ai/app/api/router.py).
- SQLAlchemy domain model and incremental Alembic history: [`yance-ai/app/models/models.py`](../../yance-ai/app/models/models.py) and [`yance-ai/alembic/versions/`](../../yance-ai/alembic/versions/).
- Separate API and durable worker processes in production composition: [`yance-ai/docker-compose.prod.yml`](../../yance-ai/docker-compose.prod.yml).
- A dedicated document worker consumes durable ingestion runs and applies the same verified service used by the synchronous API path: [`yance-ai/app/workers/document_worker.py`](../../yance-ai/app/workers/document_worker.py).
- Public webpage documents enter through a validated-IP-pinned HTTPS fetcher and then reuse the same quarantine/worker path; there is no unaudited browser fetch path.
- Explicit demo isolation at tenant level: [`yance-ai/alembic/versions/20260905_0020_investor_demo.py`](../../yance-ai/alembic/versions/20260905_0020_investor_demo.py).

## Partial / planned

- **Partial:** single-region container topology; no documented production SLA or tested disaster-recovery objective.
- **Partial:** object storage and malware scanning are abstracted/configured, while production credentials, scanner signatures and service health remain environment-specific.
- **Planned:** independently scalable retrieval and artifact-rendering workers when load data justifies separation.
