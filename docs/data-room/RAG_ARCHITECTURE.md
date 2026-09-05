# RAG Architecture

Status: **Implemented evidence-first retrieval; Partial ingestion breadth**.

```text
Policy source → normalize → immutable version → exact-span chunks
                                          │
                         metadata filters + PostgreSQL FTS + pgvector
                                          │
                                  reciprocal-rank fusion
                                          │
                           structured eligibility + exact citation
```

## Implemented

- Immutable, checksum-addressed `PolicyVersion` and exact-span `PolicyChunk`: [`yance-ai/app/models/models.py`](../../yance-ai/app/models/models.py).
- Required metadata includes issuer, region, industry, policy type, publish/effective/expiry dates, article, and URL: [`yance-ai/app/services/policies/ingestion.py`](../../yance-ai/app/services/policies/ingestion.py).
- Hybrid retrieval combines full-text and vector rankings with metadata filtering: [`yance-ai/app/services/policies/retrieval.py`](../../yance-ai/app/services/policies/retrieval.py).
- Tenant visibility rules prevent private corpus leakage: [`yance-ai/app/services/policies/visibility.py`](../../yance-ai/app/services/policies/visibility.py).
- Eligibility uses structured rules and citations: [`yance-ai/app/services/policies/eligibility.py`](../../yance-ai/app/services/policies/eligibility.py).
- Retrieval and citation tests: [`yance-ai/tests/test_rag_evidence.py`](../../yance-ai/tests/test_rag_evidence.py).

## Partial / planned

- **Partial:** deterministic reranking/fusion exists; a separately learned reranker is not claimed.
- **Partial:** upload validation accepts PDF/DOCX/XLSX/CSV/TXT, but format-specific extraction quality requires continuing eval coverage.
- **Planned:** controlled webpage URL ingestion, policy change detection, freshness SLAs, and authority-specific connectors.
