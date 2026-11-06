"""Rate-limited, size-bounded, robots-aware HTTP client for policy sources.

Design notes
------------
* Redirects are followed **manually** so that every hop is re-validated against
  the source's domain allow-list and the SSRF guard (``httpx`` auto-follow
  would hide the intermediate target).
* Bodies are streamed and truncated at ``max_bytes``; oversized responses are
  reported instead of parsed.
* ``429``/``5xx``/timeouts use bounded exponential backoff and honour
  ``Retry-After`` (capped), with a hard retry limit.
* Per-host requests are spaced by ``min_interval`` and robots ``Crawl-delay``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

from .robots import RobotsCache
from .urlguard import DEFAULT_PORTS, ResolutionError, TargetPolicy, UnsafeURLError

USER_AGENT = "YancePolicyCollector/3.0 (+https://yance.ai; policy-evidence@yance.ai)"

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int | None = None
    content: bytes = b""
    content_type: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    redirects: list[str] = field(default_factory=list)
    elapsed_ms: int = 0
    attempts: int = 0
    truncated: bool = False
    robots_denied: bool = False
    error: str | None = None
    error_kind: str | None = None  # blocked / robots / http / timeout / network / too_large

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code == 200 and not self.robots_denied

    @property
    def text(self) -> str:
        encoding = "utf-8"
        content_type = (self.content_type or "").lower()
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("charset="):
                encoding = part.split("=", 1)[1].strip() or "utf-8"
        try:
            return self.content.decode(encoding, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")

    def http_meta(self) -> dict:
        """Persisted alongside the raw evidence snapshot."""
        keep = ("content-type", "last-modified", "etag", "content-length", "server")
        return {
            "status_code": self.status_code,
            "content_type": self.content_type,
            "elapsed_ms": self.elapsed_ms,
            "attempts": self.attempts,
            "redirects": self.redirects,
            "truncated": self.truncated,
            "headers": {key: self.headers[key] for key in keep if key in self.headers},
        }


class HostRateLimiter:
    """Minimum spacing between requests to the same host."""

    def __init__(self, clock=time.monotonic, sleeper=time.sleep) -> None:
        self._clock = clock
        self._sleep = sleeper
        self._last: dict[str, float] = {}

    def wait(self, url: str, min_interval: float) -> None:
        if min_interval <= 0:
            return
        host = (urlsplit(url).hostname or "").lower()
        now = self._clock()
        previous = self._last.get(host)
        if previous is not None:
            remaining = min_interval - (now - previous)
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._clock()


class SafeFetcher:
    """All outbound policy-collection traffic goes through this class."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        target_policy: TargetPolicy,
        user_agent: str = USER_AGENT,
        max_bytes: int = 4 * 1024 * 1024,
        timeout_seconds: float = 20.0,
        min_interval_seconds: float = 2.0,
        max_retries: int = 2,
        max_redirects: int = 5,
        respect_robots: bool = True,
        clock=time.monotonic,
        sleeper=time.sleep,
    ) -> None:
        self.target_policy = target_policy
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds
        self.min_interval_seconds = min_interval_seconds
        self.max_retries = max_retries
        self.max_redirects = max_redirects
        self.respect_robots = respect_robots
        self._clock = clock
        self._sleep = sleeper
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            headers={"User-Agent": user_agent, "Accept-Language": "zh-CN,zh;q=0.9"},
        )
        self._limiter = HostRateLimiter(clock=clock, sleeper=sleeper)
        self.robots = RobotsCache(self._fetch_robots_text, clock=clock)

    # -- robots ---------------------------------------------------------
    def _fetch_robots_text(self, url: str, max_bytes: int) -> str:
        response = self._client.get(url, headers={"User-Agent": self.user_agent})
        if response.status_code >= 400:
            return ""
        return response.text[:max_bytes]

    def _robots_allows(self, url: str, policy) -> tuple[bool, float]:
        robots_policy = self.robots.policy_for(url)
        delay = robots_policy.crawl_delay or 0.0
        if not self.respect_robots:
            return True, delay
        return robots_policy.can_fetch(url, self.user_agent), delay

    # -- request --------------------------------------------------------
    def get(self, url: str, *, purpose: str = "document", min_interval: float | None = None) -> FetchResult:
        started = self._clock()
        try:
            current = self.target_policy.check(url)
        except ResolutionError as exc:
            # Transient DNS problem: report as network so the source health view
            # does not label a working source as permanently blocked.
            return FetchResult(url=url, final_url=url, error=str(exc), error_kind="network")
        except UnsafeURLError as exc:
            return FetchResult(url=url, final_url=url, error=str(exc), error_kind="blocked")

        if self.respect_robots:
            allowed, crawl_delay = self._robots_allows(current, None)
            if not allowed:
                return FetchResult(
                    url=url,
                    final_url=current,
                    robots_denied=True,
                    error="disallowed by robots.txt",
                    error_kind="robots",
                )
            if crawl_delay:
                self.min_interval_seconds = max(self.min_interval_seconds, crawl_delay)

        redirects: list[str] = []
        attempts = 0
        last_error: str | None = None
        while True:
            attempts += 1
            interval = self.min_interval_seconds if min_interval is None else min_interval
            self._limiter.wait(current, interval)
            try:
                result = self._single_request(current, purpose=purpose, redirects=redirects)
            except httpx.TimeoutException as exc:
                last_error, kind = f"timeout: {exc}", "timeout"
                result = None
            except httpx.HTTPError as exc:
                last_error, kind = f"network: {exc}", "network"
                result = None
            if result is not None:
                if result.error_kind in {"blocked", "too_large", "redirect_limit", "robots"}:
                    result.elapsed_ms = int((self._clock() - started) * 1000)
                    result.attempts = attempts
                    return result
                if result.status_code in RETRYABLE_STATUS and attempts <= self.max_retries:
                    self._sleep(self._backoff(attempts, result.headers.get("retry-after")))
                    continue
                result.elapsed_ms = int((self._clock() - started) * 1000)
                result.attempts = attempts
                if result.status_code is None:
                    result.error = result.error or last_error
                return result
            if attempts > self.max_retries:
                return FetchResult(
                    url=url,
                    final_url=current,
                    redirects=redirects,
                    error=last_error,
                    error_kind=kind,
                    attempts=attempts,
                    elapsed_ms=int((self._clock() - started) * 1000),
                )
            self._sleep(self._backoff(attempts, None))

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return min(float(retry_after), 30.0)
            except ValueError:
                try:
                    target = parsedate_to_datetime(retry_after).timestamp()
                    return max(0.0, min(target - time.time(), 30.0))
                except Exception:
                    pass
        return min(2.0**attempt, 15.0)

    def _single_request(self, url: str, *, purpose: str, redirects: list[str]) -> FetchResult:
        current = url
        for _ in range(self.max_redirects + 1):
            with self._client.stream(
                "GET",
                current,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/pdf,"
                    "application/msword,application/vnd.openxmlformats-officedocument.*;q=0.9,*/*;q=0.5",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                },
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        return FetchResult(
                            url=url,
                            final_url=current,
                            status_code=response.status_code,
                            error="redirect without location",
                            error_kind="http",
                        )
                    target = str(httpx.URL(current).join(location))
                    try:
                        target = self.target_policy.check(target)
                    except UnsafeURLError as exc:
                        return FetchResult(
                            url=url,
                            final_url=current,
                            status_code=response.status_code,
                            redirects=redirects,
                            error=f"unsafe redirect: {exc}",
                            error_kind="blocked",
                        )
                    if len(redirects) >= self.max_redirects:
                        return FetchResult(
                            url=url,
                            final_url=current,
                            status_code=response.status_code,
                            redirects=redirects,
                            error="redirect limit exceeded",
                            error_kind="redirect_limit",
                        )
                    redirects.append(target)
                    current = target
                    continue

                content_type = response.headers.get("content-type")
                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > self.max_bytes:
                    return FetchResult(
                        url=url,
                        final_url=current,
                        status_code=response.status_code,
                        content_type=content_type,
                        headers=dict(response.headers),
                        redirects=redirects,
                        error=f"declared size {declared} exceeds {self.max_bytes}",
                        error_kind="too_large",
                    )
                chunks: list[bytes] = []
                total = 0
                truncated = False
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > self.max_bytes:
                        chunks.append(chunk[: max(0, self.max_bytes - (total - len(chunk)))])
                        truncated = True
                        break
                    chunks.append(chunk)
                return FetchResult(
                    url=url,
                    final_url=current,
                    status_code=response.status_code,
                    content=b"".join(chunks),
                    content_type=content_type,
                    headers=dict(response.headers),
                    redirects=redirects,
                    truncated=truncated,
                )
        return FetchResult(
            url=url,
            final_url=current,
            redirects=redirects,
            error="redirect limit exceeded",
            error_kind="redirect_limit",
        )


def default_ports_allowed(url: str, extra: tuple[int, ...] = ()) -> tuple[int, ...]:
    return tuple({DEFAULT_PORTS[urlsplit(url).scheme], *extra})
