"""The fake-IP escape hatch must not become a hole.

A laptop behind a TUN proxy resolves every hostname into 198.18.0.0/15.  These
tests pin the exact boundaries of the opt-in that makes local download tests
possible: literal IPs are never rescued, metadata/loopback stay blocked, and the
default (empty) configuration behaves exactly as before.
"""

from __future__ import annotations

import pytest

from app.services.policy_collection.urlguard import (
    TargetPolicy,
    UnsafeURLError,
    is_blocked_ip,
)


def _policy(resolved: list[str], cidrs: tuple[str, ...] = ()) -> TargetPolicy:
    return TargetPolicy(
        allowed_domains=("www.gov.cn",),
        resolver=lambda host: list(resolved),
        dns_proxy_cidrs=cidrs,
    )


def test_fake_ip_is_blocked_by_default():
    assert is_blocked_ip("198.18.0.27") is True
    with pytest.raises(UnsafeURLError):
        _policy(["198.18.0.27"]).check("https://www.gov.cn/zc/")


def test_fake_ip_is_allowed_when_the_cidr_is_declared():
    assert is_blocked_ip("198.18.0.27", dns_proxy_cidrs=("198.18.0.0/15",)) is False
    assert _policy(["198.18.0.27"], ("198.18.0.0/15",)).check("https://www.gov.cn/zc/")


def test_metadata_and_private_ranges_survive_the_relaxation():
    cidrs = ("0.0.0.0/0",)  # the worst possible configuration
    for blocked in ("127.0.0.1", "169.254.169.254", "10.0.0.1", "192.168.1.1", "100.64.0.1"):
        assert is_blocked_ip(blocked, dns_proxy_cidrs=cidrs) is True


def test_literal_ip_in_the_url_is_never_rescued():
    policy = TargetPolicy(
        allowed_domains=("198.18.0.27",),
        resolver=lambda host: ["198.18.0.27"],
        dns_proxy_cidrs=("198.18.0.0/15",),
    )
    with pytest.raises(UnsafeURLError):
        policy.check("https://198.18.0.27/zc/")


def test_malformed_cidr_is_ignored_not_trusted():
    assert is_blocked_ip("198.18.0.27", dns_proxy_cidrs=("not-a-cidr",)) is True
