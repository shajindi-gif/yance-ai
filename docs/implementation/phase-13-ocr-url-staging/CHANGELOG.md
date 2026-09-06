# Phase 13 Changelog

## Added

- Bounded `TesseractOCRProvider` with Chinese/English configuration, page, pixel and timeout limits, per-page locators and explicit retryable unavailable state.
- Safe public-web document fetcher that accepts HTTPS/443 only, rejects every non-global DNS result, revalidates redirects and connects to the validated IP with the original TLS hostname.
- Total fetch deadline plus bounded incremental response reads, in addition to connect/read socket limits.
- Persisted URL provenance omits query values to avoid retaining signed tokens or incidental sensitive parameters.
- URL document API and Documents workspace controls. Imported bytes use the same OSS, quarantine, ClamAV, signature, parser, chunk, fact-review and audit pipeline as uploaded files.
- Sanitized static HTML text parsing that excludes scripts, styles, templates, SVG and canvas content.
- Runtime container packages for Tesseract Chinese/English OCR.
- Blocking container CI assertions for PyMuPDF and both required Tesseract language packs.
- Staging verification command and runbook for real presigned OSS upload, server checksum/content verification and in-memory ClamAV rejection smoke.
- Tracked production environment template with fail-closed malware and OCR settings; no secret values are included.
- OCR and URL security tests, including private-address denial before connection, redirect revalidation, validated-IP pinning, provenance, content limits and parser behavior.

## Changed

- Document parser version advanced to `document-parser-v2`.
- Production configuration now requires OCR to be explicitly enabled in addition to fail-closed malware scanning.
- Documents UI identifies uploaded versus web-sourced material, exposes source provenance and permits retry from `ocr_required`.

## Data changes

No migration. Existing document, content, chunk, ingestion-run, candidate, audit and analytics tables are reused.

## Verification status

- Local Tesseract smoke successfully extracted text from a generated image-only PDF with `chi_sim+eng` installed.
- Backend lint/compile passed; the clean PostgreSQL/pgvector suite passed 76 tests with 78% aggregate line coverage. Both explicit persisted E2E journeys passed.
- Frontend TypeScript and production build passed with all 35 routes.
- Authenticated Chromium Documents workspace verification passed without failed network responses or an error overlay.
- OpenAPI snapshot and ORM/migration alignment passed; latest migration downgrade/forward upgrade passed.
- Python dependency audit found no known vulnerability and the production npm audit found zero vulnerabilities.
- Local container build was attempted but could not run because the Docker daemon was unavailable; CI retains the blocking container build/SBOM/Trivy gates.

## Remaining boundaries

- Staging OSS, ClamAV signature-update and outbound network-policy evidence must be collected by an operator; repository code does not claim those checks ran.
- URL import intentionally excludes HTTP, custom ports, private networks, JavaScript-rendered and authenticated pages.
- OCR correctness is not an accuracy claim; scanned-document quality needs reviewed evaluation data.
