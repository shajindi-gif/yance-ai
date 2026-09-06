import io

import pytest

from app.services.documents.parsers import parse_document
from app.services.documents.security import DocumentIngestionError, verify_signature
from app.services.documents.url_fetcher import SafeURLFetcher


class FakeSocket:
    def settimeout(self, _timeout: float) -> None:
        return None


class FakeResponse:
    def __init__(self, status: int, payload: bytes = b"", headers: dict[str, str] | None = None):
        self.status = status
        self.stream = io.BytesIO(payload)
        self.headers = headers or {}

    def getheader(self, name: str):
        return self.headers.get(name)

    def read(self, amount: int = -1) -> bytes:
        return self.stream.read(amount)

    def read1(self, amount: int = -1) -> bytes:
        return self.read(amount)


class FakeConnection:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.sock = FakeSocket()
        self.request_args = None

    def request(self, *args, **kwargs) -> None:
        self.request_args = (args, kwargs)

    def getresponse(self) -> FakeResponse:
        return self.response

    def close(self) -> None:
        return None


def test_private_address_is_rejected_before_connection():
    connected = []
    fetcher = SafeURLFetcher(
        resolver=lambda _host: ["127.0.0.1"],
        connection_factory=lambda *args: connected.append(args),
    )
    with pytest.raises(DocumentIngestionError) as error:
        fetcher.fetch("https://example.com/company")
    assert error.value.code == "url_private_address"
    assert connected == []


def test_redirect_is_resolved_and_validated_again():
    connection = FakeConnection(
        FakeResponse(302, headers={"Location": "https://internal.example/secret"})
    )
    resolved = []

    def resolver(host: str) -> list[str]:
        resolved.append(host)
        return ["93.184.216.34"] if host == "public.example" else ["10.0.0.9"]

    fetcher = SafeURLFetcher(
        resolver=resolver,
        connection_factory=lambda *_args: connection,
    )
    with pytest.raises(DocumentIngestionError) as error:
        fetcher.fetch("https://public.example/start")
    assert error.value.code == "url_private_address"
    assert resolved == ["public.example", "internal.example"]


def test_fetch_pins_validated_ip_and_preserves_web_provenance():
    html = b"<html><head><title>Company</title><script>secret()</script></head><body><h1>Profile</h1><p>Industry: AI software</p></body></html>"
    connection = FakeConnection(
        FakeResponse(
            200,
            html,
            {"Content-Type": "text/html; charset=utf-8", "Content-Length": str(len(html))},
        )
    )
    calls = []

    def factory(host: str, address: str, timeout: float):
        calls.append((host, address, timeout))
        return connection

    fetcher = SafeURLFetcher(
        resolver=lambda _host: ["93.184.216.34"], connection_factory=factory
    )
    fetched = fetcher.fetch("https://EXAMPLE.com/company/profile?source=official#section")

    assert calls[0][0:2] == ("example.com", "93.184.216.34")
    assert connection.request_args[0] == ("GET", "/company/profile?source=official")
    assert connection.request_args[1]["headers"]["Host"] == "example.com"
    assert fetched.source_url == "https://example.com/company/profile"
    assert fetched.final_url == fetched.source_url
    assert fetched.filename == "profile.html"
    verify_signature(fetched.filename, fetched.content_type, fetched.payload)
    parsed = parse_document(fetched.filename, fetched.payload)
    assert parsed.parser == "html.parser"
    assert parsed.metadata["title"] == "Company"
    assert "Industry: AI software" in parsed.text
    assert "secret()" not in parsed.text


def test_unsupported_protocol_and_oversized_response_are_rejected(monkeypatch):
    fetcher = SafeURLFetcher(resolver=lambda _host: ["93.184.216.34"])
    with pytest.raises(DocumentIngestionError) as protocol_error:
        fetcher.fetch("http://example.com/file.pdf")
    assert protocol_error.value.code == "url_scheme"

    monkeypatch.setattr(
        "app.services.documents.url_fetcher.settings.document_upload_max_bytes", 5
    )
    connection = FakeConnection(
        FakeResponse(200, b"123456", {"Content-Type": "text/plain"})
    )
    limited = SafeURLFetcher(
        resolver=lambda _host: ["93.184.216.34"],
        connection_factory=lambda *_args: connection,
    )
    with pytest.raises(DocumentIngestionError) as size_error:
        limited.fetch("https://example.com/file.txt")
    assert size_error.value.code == "url_size_limit"


def test_total_fetch_deadline_is_enforced_before_connection(monkeypatch):
    times = iter([100.0, 131.0])
    monkeypatch.setattr("app.services.documents.url_fetcher.time.monotonic", lambda: next(times))
    connected = []
    fetcher = SafeURLFetcher(
        resolver=lambda _host: ["93.184.216.34"],
        connection_factory=lambda *args: connected.append(args),
    )
    with pytest.raises(DocumentIngestionError) as error:
        fetcher.fetch("https://example.com/file.txt")
    assert error.value.code == "url_timeout"
    assert error.value.retryable is True
    assert connected == []
