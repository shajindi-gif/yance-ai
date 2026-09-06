# Phase 12 — Production Document Intelligence

## Objective

Turn uploaded company files into reviewable, source-grounded company intelligence without treating browser upload success or unverified LLM text as parsed facts. The implementation remains additive and uses the existing tenant, company profile, object storage, analytics and audit foundations.

## Acceptance gates

1. PDF, DOCX, XLSX, CSV and TXT files are parsed by real format-specific parsers with bounded memory, archive and extracted-text limits.
2. The server computes SHA-256, verifies file signatures and runs the configured malware gate before any content is parsed.
3. Every ingestion attempt is durable, retryable and inspectable; a document cannot be represented as completed when parsing failed or OCR is required.
4. Extracted company facts are typed candidates with confidence, evidence excerpt and source locator. They do not silently change a company profile.
5. Authorized users can accept or reject candidates. Accepted values update the mutable profile draft and remain attributable to the source document and reviewer.
6. Tenant isolation is enforced on document detail, ingestion and review endpoints.
7. The existing upload and application workflows remain compatible.

## Planned files

### Schema and migration

- `yance-ai/app/models/models.py`
- `yance-ai/app/models/__init__.py`
- `yance-ai/alembic/versions/20260906_0021_document_intelligence.py`
- `yance-ai/app/schemas/schemas.py`

### Ingestion runtime

- `yance-ai/app/services/oss.py`
- `yance-ai/app/services/documents/parsers.py`
- `yance-ai/app/services/documents/security.py`
- `yance-ai/app/services/documents/intelligence.py`
- `yance-ai/app/services/documents/ingestion.py`
- `yance-ai/app/workers/document_worker.py`
- `yance-ai/app/api/routes/documents.py`
- `yance-ai/app/api/routes/admin.py`
- `yance-ai/app/api/routes/workflow.py`
- `yance-ai/app/services/admin/metrics.py`
- `yance-ai/app/core/config.py`
- `yance-ai/pyproject.toml`

### Product surface

- `website/lib/api.ts`
- `website/app/documents/page.tsx`
- `website/app/admin/page.tsx`
- relevant workspace styles if required

### Tests and operations

- `yance-ai/tests/test_document_intelligence.py`
- `yance-ai/tests/test_document_ingestion_workflow.py`
- `yance-ai/tests/test_phase1_security_boundaries.py`
- `yance-ai/tests/test_core_workflow.py`
- `.env.example`
- `.github/workflows/ci.yml`
- `yance-ai/.env.example`
- `yance-ai/Dockerfile`
- `yance-ai/docker-compose.prod.yml`
- `docs/data-room/RAG_ARCHITECTURE.md`
- `docs/data-room/SECURITY.md`
- `docs/production-readiness/RISK_ACCEPTANCE.md`
- `docs/implementation/phase-12-document-intelligence/CHANGELOG.md`

## Migration strategy

Add tenant-owned `document_ingestion_runs`, `document_contents`, `document_chunks` and `document_fact_candidates`. Existing documents remain valid. No current table or column is dropped. Existing `pending` documents can be queued explicitly after migration.

Downgrade removes only the new Phase 12 tables and indexes. It does not mutate existing document records.

## Security boundaries

- File extension, declared MIME type and detected signature must agree.
- Office archives are checked for entry count, total expanded size and compression ratio before parsing.
- Formulae and macros are never executed; macro-enabled formats remain unsupported.
- Extracted text, archive expansion, workbook rows/cells and parser work are bounded by configuration.
- Files remain quarantined until the malware gate and parser complete.
- In production, malware scanning is fail-closed when configured as required.
- Logs and API errors expose safe codes, not document content.

## Verification

- Parser unit tests with generated real TXT, CSV, DOCX, XLSX and PDF fixtures.
- Signature mismatch, archive-bomb, tenant isolation, idempotency, retry and review tests.
- Migration upgrade, one-step downgrade and forward upgrade.
- Backend lint, compile and full test suite.
- Frontend typecheck and production build.
- Manual upload-to-review check with a non-sensitive sample document.

## Explicit non-goals for this increment

- Claiming OCR support when no production OCR provider is configured. Image-only PDFs are reported as `ocr_required` with an actionable message.
- Silent auto-publication of extracted profile data.
- Arbitrary URL fetching before redirect-by-redirect SSRF controls and content provenance are independently tested.
- Treating deterministic extraction coverage as model accuracy.
