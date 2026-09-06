# Phase 12 Changelog — Production Document Intelligence

Date: 2026-09-06

## Delivered

- Added additive schema for durable ingestion attempts, canonical document content, source-locatable chunks and reviewable company fact candidates.
- Added real format-specific PDF, DOCX, XLSX, CSV and TXT parsers with extracted-text, row, cell, archive-entry, expansion and compression-ratio limits.
- Added server-authored SHA-256, file signature/Office structure validation and a clamd INSTREAM malware-scanning client.
- Made production configuration fail closed unless malware scanning is required and a ClamAV host is configured.
- Added a dedicated document worker and production ClamAV service while retaining an explicit synchronous ingestion endpoint for bounded interactive uploads.
- Added conservative deterministic Company Intelligence extraction with confidence, exact evidence excerpt and source locator.
- Added authorized human accept/reject review. Accepted facts update only the mutable profile draft; published facts preserve document provenance, method and confidence.
- Blocked quarantined, rejected and unparsed files from Application Workspace linking.
- Upgraded the Documents workspace with real status, content preview, ingestion trace, evidence candidates, review actions and retry handling.
- Added platform Admin visibility for document ingestion runs.
- Added parser/security unit coverage, a PostgreSQL API/service provenance E2E, and a Chromium Documents-workspace test.

## Migration

Revision `20260906_0021` adds only new tables and indexes. Upgrade, one-revision downgrade and forward upgrade passed against isolated PostgreSQL 18 + pgvector.

## Claim boundaries

- OCR is not claimed. Image-only PDFs return `ocr_required`.
- Webpage URL ingestion remains disabled until redirect-by-redirect SSRF controls and provenance tests are complete.
- Deterministic extraction coverage is not an accuracy claim.
- The production ClamAV container/signature lifecycle and real OSS path require staging verification; local tests validate protocol behavior and fail-closed configuration.

## Verification snapshot

- Clean-database backend suite: 67 passed; 77.80% aggregate line coverage.
- Document parser/security focused suite: five real format paths plus OCR-required, signature mismatch, Office structure and scanner fail-closed cases passed.
- Persisted document workflow: upload completion → quarantine → ingestion → chunks/candidates → human accept → profile publish with source-document provenance passed.
- Tenant-isolation check on document detail passed.
- Alembic upgrade, one-revision downgrade and forward upgrade passed through `20260906_0021`; model/migration alignment reported no pending operations.
- Frontend TypeScript and Next.js production build passed with 35 routes.
- Authenticated Chromium Documents-workspace story passed against live local Next.js, FastAPI and PostgreSQL with no failed HTTP responses or framework error overlay.
