# Document Ingestion Staging Runbook

This runbook produces staging evidence for object storage, parser/OCR runtime and malware scanning. Repository tests prove contracts; they do not prove a deployed bucket, network policy or signature-update lifecycle.

## Preconditions

- Use a dedicated staging tenant and a non-sensitive sample file.
- The API and document worker use the same private OSS bucket and tenant namespace.
- `MALWARE_SCAN_MODE=required`, `CLAMD_HOST` and `CLAMD_PORT` are configured.
- `DOCUMENT_OCR_ENABLED=true`; the runtime image contains Tesseract plus `chi_sim` and `eng` data.
- Never pass production credentials in shell history. Set `YANCE_STAGING_PASSWORD` in a protected session or use the interactive prompt.

## 1. Runtime checks

Inside the deployed API/worker image:

```bash
tesseract --version
tesseract --list-langs
python -c "import pymupdf; print(pymupdf.__version__)"
```

Confirm `chi_sim` and `eng` are listed. Record the image digest and Tesseract version in the release evidence.

## 2. Real OSS upload and ingestion

From the repository backend directory:

Load `YANCE_STAGING_PASSWORD` from the operator's secret manager, or leave it unset to use the hidden interactive prompt. Then run:

```bash
python scripts/verify_document_staging.py \
  --api-url https://staging-api.example.com \
  --email staging-operator@example.com \
  --sample /secure/path/non-sensitive-company-profile.pdf
```

The command obtains a real presigned URL, uploads the exact bytes, completes and executes ingestion, and checks the server-authored SHA-256, canonical content and chunks. A pass prints only the document identifier, parser, chunk count and abbreviated checksum.

For a scanned PDF, require `parser=ocr:tesseract`. Manually inspect the extracted preview through the authenticated Documents workspace; do not treat successful OCR as correctness evidence.

## 3. ClamAV fail-closed smoke

Run the verifier from an environment with the same ClamAV settings as the document worker:

```bash
python scripts/verify_document_staging.py \
  --api-url https://staging-api.example.com \
  --email staging-operator@example.com \
  --sample /secure/path/non-sensitive-company-profile.txt \
  --check-clamav
```

The antivirus test signature is assembled in memory and is never written to the repository. Passing requires ClamAV to reject it as `malware_detected`; scanner unavailability or a skipped scan fails the command.

## 4. Safe URL import

In the Documents workspace, import a controlled public HTTPS test page. Verify:

- the record source is `url` and the normalized source URL is visible;
- ingestion reaches `completed` only after malware scan and parsing;
- redirects and final host are recorded;
- an `https://127.0.0.1/`, RFC1918, link-local and non-HTTPS test is rejected;
- an oversized or unsupported MIME response is rejected.

Never use cloud metadata endpoints or internal customer services as negative-test targets. Unit tests cover those address classes without making a connection.

## 5. Evidence to retain

- deployment identifier and immutable image digest;
- redacted verifier output and UTC timestamp;
- ClamAV engine/signature database versions and update status;
- test document IDs and expected deletion date;
- operator and reviewer approval;
- failures, remediation and rerun result.

Delete staging fixtures according to the tenant retention policy. Do not copy extracted customer content into tickets or logs.

## Failure policy

- OSS checksum/content mismatch: block document ingestion release.
- ClamAV unavailable or not detecting the in-memory test signature: block customer uploads.
- OCR unavailable: keep scanned PDFs in `ocr_required`; do not mark them parsed.
- URL private-address or redirect validation regression: disable `DOCUMENT_URL_IMPORT_ENABLED` and block URL imports.
