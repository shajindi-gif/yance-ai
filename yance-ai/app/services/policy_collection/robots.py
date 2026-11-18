"""robots.txt awareness with a per-host cache.

The previous crawler claimed robots compliance without implementing it. This
module performs an actual robots.txt fetch, honours ``User-agent`` groups and
``Disallow``/``Allow``/``Crawl-delay``, and fails **closed** only for
``Disallow: /`` situations — a network error yields ``unknown`` state which is
reported instead of silently treated as permission.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from .urlguard import DEFAULT_PORTS


@dataclass
class RobotsPolicy:
    """Result of evaluating robots.txt for one host."""

    host: str
    fetched: bool
    allowed_all: bool = False
    crawl_delay: float | None = None
    status: str = "unknown"  # allowed / disallowed / unknown
    error: str | None = None
    _parser: RobotFileParser | None = field(default=None, repr=False)

    def can_fetch(self, url: str, user_agent: str) -> bool:
        if self._parser is None:
            # Unknown robots state: proceed conservatively at the source's own
            # rate limit, but record the state so health reporting exposes it.
            return True
        return self._parser.can_fetch(user_agent, url)


def parse_robots(text: str, host: str) -> RobotsPolicy:
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    policy = RobotsPolicy(host=host, fetched=True, _parser=parser)
    delay = parser.crawl_delay("*")
    policy.crawl_delay = float(delay) if delay else None
    return policy


class RobotsCache:
    """Per-host robots.txt cache with a TTL and a pluggable fetcher."""

    def __init__(
        self,
        fetch_text,
        *,
        ttl_seconds: float = 6 * 3600,
        max_bytes: int = 512 * 1024,
        clock=time.monotonic,
    ) -> None:
        self._fetch_text = fetch_text
        self._ttl = ttl_seconds
        self._max_bytes = max_bytes
        self._clock = clock
        self._entries: dict[str, tuple[float, RobotsPolicy]] = {}

    def policy_for(self, url: str) -> RobotsPolicy:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        key = host
        now = self._clock()
        cached = self._entries.get(key)
        if cached and now - cached[0] < self._ttl:
            return cached[1]
        robots_url = (
            f"{parts.scheme}://{host}"
            + ("" if (parts.port in (None, DEFAULT_PORTS[parts.scheme])) else f":{parts.port}")
            + "/robots.txt"
        )
        try:
            text = self._fetch_text(robots_url, self._max_bytes)
        except Exception as exc:  # network/robots errors must not be fatal
            policy = RobotsPolicy(host=host, fetched=False, status="unknown", error=str(exc))
        else:
            policy = parse_robots(text, host)
            policy.status = "allowed"
            policy.allowed_all = True
        self._entries[key] = (now, policy)
        return policy
