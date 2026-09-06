import io
import socket
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


class DocumentIngestionError(Exception):
    def __init__(self, code: str, safe_message: str, *, retryable: bool = False) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable


@dataclass(frozen=True)
class MalwareScanResult:
    status: str
    engine: str
    signature: str | None = None


OFFICE_MARKERS = {
    ".docx": "word/document.xml",
    ".xlsx": "xl/workbook.xml",
}


def verify_signature(filename: str, content_type: str, payload: bytes) -> None:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        if not payload.startswith(b"%PDF-"):
            raise DocumentIngestionError("signature_mismatch", "File content is not a valid PDF")
        return
    if extension in OFFICE_MARKERS:
        if not payload.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            raise DocumentIngestionError(
                "signature_mismatch", "Office document signature does not match its extension"
            )
        validate_office_archive(payload, extension)
        return
    if extension in {".txt", ".csv", ".html", ".htm"}:
        if b"\x00" in payload[:8192]:
            raise DocumentIngestionError("binary_text", "Text document contains binary data")
        if extension in {".html", ".htm"} and content_type.lower() != "text/html":
            raise DocumentIngestionError(
                "signature_mismatch", "Web document content type does not match its extension"
            )
        return
    raise DocumentIngestionError("unsupported_type", f"Unsupported document type: {content_type}")


def validate_office_archive(payload: bytes, extension: str) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            names = {item.filename for item in infos}
            if "[Content_Types].xml" not in names or OFFICE_MARKERS[extension] not in names:
                raise DocumentIngestionError(
                    "office_structure_invalid", "Office document structure is invalid"
                )
            if len(infos) > settings.document_archive_max_entries:
                raise DocumentIngestionError(
                    "archive_entry_limit", "Office document contains too many archive entries"
                )
            total_uncompressed = sum(item.file_size for item in infos)
            if total_uncompressed > settings.document_archive_max_uncompressed_bytes:
                raise DocumentIngestionError(
                    "archive_expansion_limit", "Office document expands beyond the safety limit"
                )
            compressed = sum(max(item.compress_size, 1) for item in infos)
            if total_uncompressed / max(compressed, 1) > settings.document_archive_max_compression_ratio:
                raise DocumentIngestionError(
                    "archive_compression_ratio", "Office document compression ratio is unsafe"
                )
            if any(item.flag_bits & 0x1 for item in infos):
                raise DocumentIngestionError(
                    "encrypted_archive", "Encrypted Office documents are not supported"
                )
    except zipfile.BadZipFile as exc:
        raise DocumentIngestionError(
            "office_structure_invalid", "Office document structure is invalid"
        ) from exc


class ClamAVScanner:
    """Small clamd INSTREAM client; document bytes never leave the configured scanner."""

    engine = "clamd"

    def scan(self, payload: bytes) -> MalwareScanResult:
        if settings.malware_scan_mode == "disabled":
            return MalwareScanResult(status="skipped", engine="disabled")
        if not settings.clamd_host:
            if settings.malware_scan_mode == "optional":
                return MalwareScanResult(status="unavailable", engine=self.engine)
            raise DocumentIngestionError(
                "malware_scanner_unavailable",
                "Document security scanner is unavailable; try again later",
                retryable=True,
            )
        try:
            with socket.create_connection(
                (settings.clamd_host, settings.clamd_port),
                timeout=settings.clamd_timeout_seconds,
            ) as connection:
                connection.settimeout(settings.clamd_timeout_seconds)
                connection.sendall(b"zINSTREAM\0")
                view = memoryview(payload)
                for offset in range(0, len(payload), 64 * 1024):
                    chunk = view[offset : offset + 64 * 1024]
                    connection.sendall(struct.pack("!I", len(chunk)))
                    connection.sendall(chunk)
                connection.sendall(struct.pack("!I", 0))
                response = connection.recv(4096).decode("utf-8", errors="replace").strip("\0\r\n")
        except OSError as exc:
            if settings.malware_scan_mode == "optional":
                return MalwareScanResult(status="unavailable", engine=self.engine)
            raise DocumentIngestionError(
                "malware_scanner_unavailable",
                "Document security scanner is unavailable; try again later",
                retryable=True,
            ) from exc
        if response.endswith(" OK"):
            return MalwareScanResult(status="clean", engine=self.engine)
        if response.endswith(" FOUND"):
            raise DocumentIngestionError(
                "malware_detected", "Document was rejected by the security scanner"
            )
        raise DocumentIngestionError(
            "malware_scan_error", "Document security scan could not be completed", retryable=True
        )
