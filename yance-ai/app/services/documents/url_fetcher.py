import http.client
import ipaddress
import re
import socket
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from app.core.config import settings
from app.services.documents.security import DocumentIngestionError

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
CONTENT_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
    "text/html": ".html",
    "text/plain": ".txt",
}


@dataclass(frozen=True)
class FetchedDocument:
    payload: bytes
    filename: str
    content_type: str
    source_url: str
    final_url: str
    redirects: int


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to an already validated IP while using the URL host for TLS SNI."""

    def __init__(self, host: str, address: str, timeout: float) -> None:
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self._validated_address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._validated_address, 443), timeout=self.timeout
        )
        try:
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)
        except Exception:
            raw_socket.close()
            raise


Resolver = Callable[[str], list[str]]
ConnectionFactory = Callable[[str, str, float], http.client.HTTPSConnection]


def _resolve(host: str) -> list[str]:
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise DocumentIngestionError(
            "url_dns_failed", "Web address could not be resolved", retryable=True
        ) from exc
    return list(dict.fromkeys(record[4][0] for record in records))


def _normalize_url(value: str) -> str:
    if len(value) > 2048:
        raise DocumentIngestionError("url_invalid", "Web address is too long")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise DocumentIngestionError("url_invalid", "Web address contains invalid characters")
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() != "https":
        raise DocumentIngestionError("url_scheme", "Only HTTPS web addresses are supported")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise DocumentIngestionError("url_invalid", "Web address host or credentials are invalid")
    try:
        port = parsed.port
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError) as exc:
        raise DocumentIngestionError("url_invalid", "Web address host is invalid") from exc
    if not host or port not in {None, 443}:
        raise DocumentIngestionError("url_port", "Only the standard HTTPS port is supported")
    netloc = host if ":" not in host else f"[{host}]"
    path = parsed.path or "/"
    return urlunsplit(("https", netloc, path, parsed.query, ""))


def _provenance_url(value: str) -> str:
    """Keep stable public provenance without persisting possibly sensitive query values."""
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _validated_addresses(host: str, resolver: Resolver) -> list[str]:
    addresses = resolver(host)
    if not addresses:
        raise DocumentIngestionError("url_dns_failed", "Web address has no network address")
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as exc:
            raise DocumentIngestionError("url_dns_failed", "Web address resolved incorrectly") from exc
        if not parsed.is_global:
            raise DocumentIngestionError(
                "url_private_address", "Private or non-public web addresses are not allowed"
            )
    return addresses


def _safe_filename(url: str, content_type: str) -> str:
    path_name = unquote(PurePosixPath(urlsplit(url).path).name)
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", path_name)[:160]
    extension = CONTENT_EXTENSIONS[content_type]
    if not cleaned or cleaned in {".", ".."}:
        cleaned = f"web-document{extension}"
    if PurePosixPath(cleaned).suffix.lower() != extension:
        cleaned = f"{PurePosixPath(cleaned).stem or 'web-document'}{extension}"
    return cleaned


def _read_bounded(
    response: http.client.HTTPResponse,
    connection: http.client.HTTPSConnection,
    *,
    limit: int,
    deadline: float,
) -> bytes:
    chunks: list[bytes] = []
    size = 0
    read = getattr(response, "read1", response.read)
    while True:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise DocumentIngestionError(
                "url_timeout", "Web document fetch timed out", retryable=True
            )
        if connection.sock is not None:
            connection.sock.settimeout(
                min(settings.document_url_read_timeout_seconds, remaining_seconds)
            )
        chunk = read(min(64 * 1024, limit + 1 - size))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise DocumentIngestionError("url_size_limit", "Web document exceeds the size limit")


class SafeURLFetcher:
    def __init__(
        self,
        *,
        resolver: Resolver = _resolve,
        connection_factory: ConnectionFactory = PinnedHTTPSConnection,
    ) -> None:
        self.resolver = resolver
        self.connection_factory = connection_factory

    def fetch(self, source_url: str) -> FetchedDocument:
        if not settings.document_url_import_enabled:
            raise DocumentIngestionError("url_import_disabled", "Web import is not enabled")
        initial_url = _normalize_url(source_url)
        current_url = initial_url
        visited: set[str] = set()
        deadline = time.monotonic() + settings.document_url_total_timeout_seconds
        for redirect_count in range(settings.document_url_max_redirects + 1):
            if current_url in visited:
                raise DocumentIngestionError("url_redirect_loop", "Web address redirects in a loop")
            visited.add(current_url)
            parsed = urlsplit(current_url)
            host = parsed.hostname or ""
            addresses = _validated_addresses(host, self.resolver)
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                raise DocumentIngestionError(
                    "url_timeout", "Web document fetch timed out", retryable=True
                )
            connection = self.connection_factory(
                host,
                addresses[0],
                min(settings.document_url_connect_timeout_seconds, remaining_seconds),
            )
            path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
            try:
                connection.request(
                    "GET",
                    path,
                    headers={
                        "Host": host,
                        "Accept": ", ".join(CONTENT_EXTENSIONS),
                        "User-Agent": "Yance-Document-Importer/1.0",
                        "Connection": "close",
                    },
                )
                response = connection.getresponse()
                if response.status in REDIRECT_STATUSES:
                    location = response.getheader("Location")
                    if not location:
                        raise DocumentIngestionError(
                            "url_redirect_invalid", "Web address returned an invalid redirect"
                        )
                    if redirect_count >= settings.document_url_max_redirects:
                        raise DocumentIngestionError(
                            "url_redirect_limit", "Web address exceeded the redirect limit"
                        )
                    current_url = _normalize_url(urljoin(current_url, location))
                    continue
                if response.status < 200 or response.status >= 300:
                    raise DocumentIngestionError(
                        "url_http_error", f"Web address returned HTTP {response.status}", retryable=True
                    )
                content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
                if content_type not in CONTENT_EXTENSIONS:
                    raise DocumentIngestionError(
                        "url_content_type", "Web address did not return a supported document type"
                    )
                content_length = response.getheader("Content-Length")
                if content_length and int(content_length) > settings.document_upload_max_bytes:
                    raise DocumentIngestionError("url_size_limit", "Web document exceeds the size limit")
                payload = _read_bounded(
                    response,
                    connection,
                    limit=settings.document_upload_max_bytes,
                    deadline=deadline,
                )
                if not payload:
                    raise DocumentIngestionError("empty_document", "Web document is empty")
                return FetchedDocument(
                    payload=payload,
                    filename=_safe_filename(current_url, content_type),
                    content_type=content_type,
                    source_url=_provenance_url(initial_url),
                    final_url=_provenance_url(current_url),
                    redirects=redirect_count,
                )
            except DocumentIngestionError:
                raise
            except (OSError, ssl.SSLError, http.client.HTTPException, ValueError) as exc:
                raise DocumentIngestionError(
                    "url_fetch_failed", "Web document could not be fetched", retryable=True
                ) from exc
            finally:
                connection.close()
        raise DocumentIngestionError("url_redirect_limit", "Web address exceeded the redirect limit")


def get_safe_url_fetcher() -> SafeURLFetcher:
    return SafeURLFetcher()
