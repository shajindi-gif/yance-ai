"""URL normalisation and SSRF-safe destination checks.

Every request the collector makes passes through :func:`validate_target` once
per hop (initial URL and each redirect). The guard is deliberately deny-first:

* only ``http``/``https``;
* no userinfo, no non-standard ports unless the source explicitly allows them;
* the host must match an allow-listed domain (exact or subdomain — never a bare
  top-level suffix such as ``gov.cn``);
* every resolved IP address must be public (loopback, private, link-local,
  CGNAT, multicast, reserved and the cloud metadata address are rejected).

DNS is resolved by the caller so tests can inject a deterministic resolver.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_PORTS = {"http": 80, "https": 443}

# Query parameters that never change the addressed document.
TRACKING_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "spm",
    "from",
    "share_source",
    "share_medium",
    "timestamp",
    "_t",
}

CLOUD_METADATA_HOSTS = {"metadata.tencentyun.com", "metadata.google.internal"}


class UnsafeURLError(ValueError):
    """Raised when a target URL violates the collector's access policy."""


def normalize_url(url: str) -> str:
    """Return a stable canonical form used for de-duplication keys."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme not in DEFAULT_PORTS:
        raise UnsafeURLError(f"unsupported scheme: {scheme or '(none)'}")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise UnsafeURLError("missing host")
    port = parts.port
    netloc = host if port in (None, DEFAULT_PORTS[scheme]) else f"{host}:{port}"
    path = parts.path or "/"
    # Collapse duplicate slashes but keep semantics of the original path.
    while "//" in path:
        path = path.replace("//", "/")
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMETERS
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def host_matches(host: str, allowed_domains: Iterable[str]) -> bool:
    """Exact host or true subdomain match. ``gov.cn`` must not match ``x.gov.cn``."""
    candidate = host.lower().rstrip(".")
    for domain in allowed_domains:
        entry = domain.lower().strip().lstrip(".")
        if not entry:
            continue
        if candidate == entry or candidate.endswith("." + entry):
            return True
    return False


def is_blocked_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return True
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or address in ipaddress.ip_network("100.64.0.0/10")  # CGNAT
        or address in ipaddress.ip_network("169.254.169.254/32")  # cloud metadata
    )


class ResolutionError(UnsafeURLError):
    """DNS failure — a network condition, not a policy block.

    Kept as a subclass of :class:`UnsafeURLError` so callers that only care about
    "do not proceed" keep working, while fetch() can report it as a transient
    network error instead of a permanent block.
    """


def resolve_ips(host: str) -> list[str]:
    """Resolve a host to its IPs; DNS failures are surfaced to the caller."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise ResolutionError(f"dns resolution failed: {host}") from exc
    addresses: list[str] = []
    for info in infos:
        address = info[4][0]
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise ResolutionError(f"dns returned no address: {host}")
    return addresses


@dataclass(frozen=True)
class TargetPolicy:
    """Per-source destination policy derived from ``policy_sources.yaml``."""

    allowed_domains: tuple[str, ...]
    allowed_ports: tuple[int, ...] = (80, 443)
    resolver: Callable[[str], list[str]] = resolve_ips

    def check(self, url: str) -> str:
        """Validate one hop and return its canonical form."""
        canonical = normalize_url(url)
        parts = urlsplit(canonical)
        if parts.username or parts.password:
            raise UnsafeURLError("credentials in URL are not allowed")
        host = parts.hostname or ""
        if host in CLOUD_METADATA_HOSTS:
            raise UnsafeURLError("cloud metadata endpoint is blocked")
        if not host_matches(host, self.allowed_domains):
            raise UnsafeURLError(f"host not allow-listed: {host}")
        port = parts.port or DEFAULT_PORTS[parts.scheme]
        if port not in self.allowed_ports:
            raise UnsafeURLError(f"port not allowed: {port}")
        # A literal IP must also be public even if it somehow matched a domain.
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            if is_blocked_ip(str(literal)):
                raise UnsafeURLError("target IP is not public")
            return canonical
        for address in self.resolver(host):
            if is_blocked_ip(address):
                raise UnsafeURLError(f"host resolves to a blocked address: {address}")
        return canonical


def validate_target(url: str, allowed_domains: Iterable[str]) -> str:
    """Convenience wrapper used by CLI diagnostics and tests."""
    return TargetPolicy(tuple(allowed_domains)).check(url)
