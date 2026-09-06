"""Verify staging object storage, ingestion and malware gates with non-sensitive input."""

import argparse
import getpass
import hashlib
import mimetypes
import os
from pathlib import Path

import httpx

from app.services.documents.security import ClamAVScanner, DocumentIngestionError

SUPPORTED_TYPES = {
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def verify_upload(args: argparse.Namespace) -> None:
    sample = Path(args.sample).resolve()
    payload = sample.read_bytes()
    content_type = SUPPORTED_TYPES.get(sample.suffix.lower()) or mimetypes.guess_type(sample.name)[0]
    if content_type not in SUPPORTED_TYPES.values():
        raise SystemExit("Sample must be PDF, DOCX, XLSX, CSV or TXT")
    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=args.timeout) as client:
        password = os.getenv("YANCE_STAGING_PASSWORD") or getpass.getpass(
            "Staging password: "
        )
        auth = _request(
            client,
            "POST",
            "/api/v1/auth/login",
            data={"username": args.email, "password": password},
        )
        client.headers["Authorization"] = f"Bearer {auth['access_token']}"
        company_id = args.company_id
        if not company_id:
            companies = _request(client, "GET", "/api/v1/companies")
            if not companies:
                raise SystemExit("No staging company exists; pass --company-id after creating one")
            company_id = companies[0]["id"]
        presigned = _request(
            client,
            "POST",
            "/api/v1/documents/presign-upload",
            json={
                "filename": sample.name,
                "content_type": content_type,
                "company_id": company_id,
                "size_bytes": len(payload),
            },
        )
        upload = httpx.put(
            presigned["upload_url"],
            content=payload,
            headers=presigned["required_headers"],
            timeout=args.timeout,
        )
        upload.raise_for_status()
        document_id = presigned["document"]["id"]
        _request(client, "POST", f"/api/v1/documents/{document_id}/complete", json={})
        detail = _request(
            client,
            "POST",
            f"/api/v1/documents/{document_id}/ingest",
            json={"force": False},
        )
        document = detail["document"]
        expected_checksum = hashlib.sha256(payload).hexdigest()
        if document["ingestion_status"] != "completed":
            raise SystemExit(f"Ingestion did not complete: {document['ingestion_status']}")
        if document["checksum_sha256"] != expected_checksum:
            raise SystemExit("Server checksum does not match the uploaded bytes")
        if not detail["content"] or detail["chunk_count"] < 1:
            raise SystemExit("Ingestion completed without canonical content or chunks")
        print(
            f"PASS upload document={document_id} parser={detail['content']['parser']} "
            f"chunks={detail['chunk_count']} checksum={expected_checksum[:12]}..."
        )


def verify_clamav() -> None:
    test_signature = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    try:
        ClamAVScanner().scan(test_signature)
    except DocumentIngestionError as exc:
        if exc.code == "malware_detected":
            print("PASS ClamAV rejected the in-memory antivirus test signature")
            return
        raise SystemExit(f"ClamAV smoke failed with {exc.code}: {exc.safe_message}") from exc
    raise SystemExit("ClamAV did not reject the antivirus test signature")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--company-id")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--check-clamav", action="store_true")
    args = parser.parse_args()
    verify_upload(args)
    if args.check_clamav:
        verify_clamav()


if __name__ == "__main__":
    main()
