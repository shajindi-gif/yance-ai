# RAG Architecture

Status: **Implemented evidence-first retrieval and bounded company-document ingestion; Partial OCR/URL breadth**.

```text
Policy source → normalize → immutable version → exact-span chunks
                                          │
                         metadata filters + PostgreSQL FTS + pgvector
                                          │
                                  reciprocal-rank fusion
                                          │
                           structured eligibility + exact citation
```

```text
Company file → quarantine → signature/archive/malware gates → format parser
             → canonical content → source-locatable chunks → fact candidates
             → human accept/reject → profile draft → immutable published facts
```

## Implemented

- Immutable, checksum-addressed `PolicyVersion` and exact-span `PolicyChunk`: [`yance-ai/app/models/models.py`](../../yance-ai/app/models/models.py).
- Required metadata includes issuer, region, industry, policy type, publish/effective/expiry dates, article, and URL: [`yance-ai/app/services/policies/ingestion.py`](../../yance-ai/app/services/policies/ingestion.py).
- Hybrid retrieval combines full-text and vector rankings with metadata filtering: [`yance-ai/app/services/policies/retrieval.py`](../../yance-ai/app/services/policies/retrieval.py).
- Tenant visibility rules prevent private corpus leakage: [`yance-ai/app/services/policies/visibility.py`](../../yance-ai/app/services/policies/visibility.py).
- Eligibility uses structured rules and citations: [`yance-ai/app/services/policies/eligibility.py`](../../yance-ai/app/services/policies/eligibility.py).
- Retrieval and citation tests: [`yance-ai/tests/test_rag_evidence.py`](../../yance-ai/tests/test_rag_evidence.py).
- Real PDF, DOCX, XLSX, CSV and TXT parsing with bounded extraction and explicit OCR-required status: [`yance-ai/app/services/documents/parsers.py`](../../yance-ai/app/services/documents/parsers.py).
- Durable document runs, canonical contents/chunks and evidence-bearing company fact candidates: [`yance-ai/app/services/documents/ingestion.py`](../../yance-ai/app/services/documents/ingestion.py).
- Human-reviewed candidates update only the profile draft; published `CompanyFact` rows preserve source document, method and confidence: [`yance-ai/app/api/routes/documents.py`](../../yance-ai/app/api/routes/documents.py) and [`yance-ai/app/services/company_profiles.py`](../../yance-ai/app/services/company_profiles.py).

## Partial / planned

- **Partial:** deterministic reranking/fusion exists; a separately learned reranker is not claimed.
- **Partial:** deterministic fact extraction intentionally favors precision and explicit labels; breadth requires reviewed production eval evidence before expansion.
- **Partial:** scanned/image-only PDFs are reported as `ocr_required`; no OCR provider is claimed yet.
- **Planned:** redirect-by-redirect SSRF-tested webpage ingestion, OCR provider integration, policy change detection, freshness SLAs, and authority-specific connectors.
