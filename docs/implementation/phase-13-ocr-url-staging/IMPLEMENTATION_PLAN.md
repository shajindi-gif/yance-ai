# Phase 13 — OCR, Safe URL Ingestion and Staging Verification

## Objective

Close the three explicit production gaps left by Phase 12: scanned PDF extraction, webpage URL ingestion, and repeatable verification against real object storage and malware scanning. The change extends the existing document intelligence pipeline and does not add a second ingestion path.

## Acceptance gates

1. Image-only PDFs can be OCRed through a bounded provider abstraction. Production uses local Tesseract with Chinese and English language packs; disabled or unavailable OCR remains an explicit, retryable `ocr_required` state.
2. URL imports accept HTTPS only and validate every redirect. Private, loopback, link-local, reserved and non-global destinations are rejected before a connection is made.
3. URL fetching pins the validated IP while preserving the original hostname for TLS and `Host`, preventing a second DNS lookup from bypassing the validation decision.
4. Download bytes, redirects, timeouts and accepted content types are bounded. HTML is converted to clean text without executing scripts; supported document responses reuse the Phase 12 parsers.
5. URL-imported content is stored in the tenant object namespace, malware scanned, checksummed, parsed, chunked and reviewed through the same durable ingestion records as uploaded files.
6. The Documents workspace exposes URL import without implying support for arbitrary protocols or unaudited browsing.
7. A staging smoke command verifies real presigned upload, server checksum, extraction and ClamAV rejection without committing malware signatures or secrets.

## Planned files

### Runtime

- `yance-ai/app/core/config.py`
- `yance-ai/app/services/documents/ocr.py`
- `yance-ai/app/services/documents/url_fetcher.py`
- `yance-ai/app/services/documents/parsers.py`
- `yance-ai/app/services/documents/ingestion.py`
- `yance-ai/app/services/oss.py`
- `yance-ai/app/api/routes/documents.py`
- `yance-ai/app/schemas/schemas.py`
- `yance-ai/pyproject.toml`
- `yance-ai/requirements.txt`

### Product surface

- `website/lib/api.ts`
- `website/app/documents/page.tsx`

### Operations and tests

- `yance-ai/tests/test_document_ocr.py`
- `yance-ai/tests/test_safe_url_ingestion.py`
- `yance-ai/tests/test_document_ingestion_workflow.py`
- `yance-ai/scripts/verify_document_staging.py`
- `yance-ai/Dockerfile`
- `.env.example`
- `yance-ai/.env.example`
- `docs/production-readiness/DOCUMENT_INGESTION_RUNBOOK.md`
- `docs/data-room/RAG_ARCHITECTURE.md`
- `docs/data-room/SECURITY.md`
- `docs/implementation/phase-13-ocr-url-staging/CHANGELOG.md`

## Migration strategy

No database migration is required. Existing `Document.source_type`, `metadata_json`, durable ingestion runs, content, chunks and candidate tables already model URL provenance and OCR parser metadata. URL documents use the same tenant ownership and lifecycle fields as file uploads.

## Security boundaries

- HTTPS and port 443 only; credentials and fragments are rejected.
- Each hop is resolved and checked independently; all accepted addresses must be globally routable.
- The connection uses a previously validated IP and TLS SNI for the original hostname.
- Redirect count, response bytes and socket timeouts are configuration bounded.
- Ambient proxy settings, cookies and browser credentials are not used.
- HTML scripts, styles, forms and hidden executable content are not interpreted.
- OCR page count, render DPI, wall-clock timeout and output size are bounded.
- Logs and audit records contain normalized URLs and operational metadata, not extracted customer content.

## Verification

- OCR provider contract and image-only PDF fallback tests with deterministic stubs.
- URL normalization, private-address denial, redirect revalidation, size limit, MIME handling and pinned-connection tests.
- Backend lint, compile and complete test suite.
- Frontend typecheck, production build and Documents workspace browser verification.
- Container image includes Tesseract Chinese and English language data.
- Staging runbook covers OSS, worker and ClamAV smoke checks with non-sensitive fixtures.

## Explicit non-goals

- General-purpose web crawling, JavaScript rendering or authenticated websites.
- Automatic trust in webpage facts; extracted company facts still require human review.
- Hiding missing OCR runtime configuration behind a successful status.
- Claiming staging verification has run unless operators execute the smoke command against deployed credentials.
