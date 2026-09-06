# RAG Architecture

Status: **Implemented evidence-first retrieval and bounded company-document/OCR/URL ingestion; Partial production breadth**.

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
Company file/URL → SSRF gate → quarantine → signature/archive/malware gates → parser/OCR
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
- Real PDF, DOCX, XLSX, CSV, TXT and sanitized HTML parsing with bounded extraction: [`yance-ai/app/services/documents/parsers.py`](../../yance-ai/app/services/documents/parsers.py).
- Bounded Tesseract OCR provider with per-page source locators, page/pixel/time limits and explicit unavailable state: [`yance-ai/app/services/documents/ocr.py`](../../yance-ai/app/services/documents/ocr.py).
- HTTPS-only, redirect-by-redirect URL import with global-address validation and validated-IP connection pinning: [`yance-ai/app/services/documents/url_fetcher.py`](../../yance-ai/app/services/documents/url_fetcher.py).
- Durable document runs, canonical contents/chunks and evidence-bearing company fact candidates: [`yance-ai/app/services/documents/ingestion.py`](../../yance-ai/app/services/documents/ingestion.py).
- Human-reviewed candidates update only the profile draft; published `CompanyFact` rows preserve source document, method and confidence: [`yance-ai/app/api/routes/documents.py`](../../yance-ai/app/api/routes/documents.py) and [`yance-ai/app/services/company_profiles.py`](../../yance-ai/app/services/company_profiles.py).

## Partial / planned

- **Partial:** deterministic reranking/fusion exists; a separately learned reranker is not claimed.
- **Partial:** deterministic fact extraction intentionally favors precision and explicit labels; breadth requires reviewed production eval evidence before expansion.
- **Partial:** OCR extraction is implemented and locally smoke-tested, but domain accuracy requires a reviewed scanned-document eval set.
- **Partial:** URL import handles public static HTTPS content only; JavaScript rendering, authenticated sites and general crawling are intentionally out of scope.
- **Planned:** policy change detection, freshness SLAs, authority-specific connectors and staging evidence for real OSS/ClamAV operations.
