"""Tests for the configured ``open_api`` list adapter and list navigation filtering.

The fixtures below are synthetic HTTP responses shaped like the official NDRC
search API. They prove the adapter's behaviour only; real reachability of each
government endpoint is recorded separately in
``docs/policy-collection-test-report.md``.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.policy_collection.adapters import ListUnavailable, OpenApiListAdapter
from app.services.policy_collection.catalog import SourceDefinition
from app.services.policy_collection.extract import extract_list_entries
from app.services.policy_collection.fetch import SafeFetcher
from app.services.policy_collection.urlguard import TargetPolicy

LIST_PAGE = """<html><body><div id="result"></div>
<script>var pageParam={key: 'ABCDEF0123456789ABCDEF0123456789'};</script>
</body></html>"""


def _source(**overrides) -> SourceDefinition:
    base = dict(
        source_id="test_api",
        name="测试接口来源",
        authority="测试机构",
        level="national",
        province=None,
        city=None,
        channel="policy_document",
        entry_url="https://example.gov.cn/wjk/index.html",
        allowed_domains=("example.gov.cn", "api.example.gov.cn"),
        adapter="open_api",
        enabled=True,
        max_pages=3,
        api={
            "url": "https://api.example.gov.cn/api/query",
            "key_from_page": "key:\\s*'([^']+)'",
            "items_path": "data.resultList",
            "title_field": "title",
            "url_field": "url",
            "date_field": "docDate",
            "page_param": "page",
            "page_size_param": "pageSize",
            "page_size": 2,
            "first_page": 1,
            "max_pages": 2,
            "params": {"qt": "", "tab": "", "siteCode": "bm04000fgk"},
        },
    )
    base.update(overrides)
    return SourceDefinition(**base)


def _fetcher(handler) -> SafeFetcher:
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return SafeFetcher(
        client=client,
        target_policy=TargetPolicy(
            allowed_domains=("example.gov.cn", "api.example.gov.cn"),
            resolver=lambda _host: ["93.184.216.34"],
        ),
        user_agent="test",
        min_interval_seconds=0,
        max_retries=0,
        respect_robots=False,
        sleeper=lambda _s: None,
    )


def test_configured_api_reads_visit_key_and_paginates():
    seen_keys: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/index.html"):
            return httpx.Response(200, text=LIST_PAGE)
        seen_keys.append(request.url.params.get("key", ""))
        page = int(request.url.params.get("page", "1"))
        rows = {
            1: [
                {"title": "关于组织申报重点项目资金的通知", "url": "https://example.gov.cn/a.html",
                 "docDate": "2026-03-01"},
                {"title": "关于印发专项资金管理办法的通知", "url": "https://example.gov.cn/b.html",
                 "docDate": "2026-02-20"},
            ],
            2: [
                {"title": "关于下达补助资金的通知", "url": "https://example.gov.cn/c.html",
                 "docDate": "2026-01-11"},
            ],
        }[page]
        return httpx.Response(200, text=json.dumps({"ok": True, "data": {"resultList": rows}}))

    fetch = OpenApiListAdapter().fetch(_fetcher(handler), _source(), max_pages=3)

    assert fetch.adapter_used == "open_api"
    assert [entry.title for entry in fetch.entries] == [
        "关于组织申报重点项目资金的通知",
        "关于印发专项资金管理办法的通知",
        "关于下达补助资金的通知",
    ]
    assert fetch.pages_fetched == 2, "short last page must stop pagination"
    assert entries_dates(fetch.entries) == ["2026-03-01", "2026-02-20", "2026-01-11"]
    assert seen_keys and set(seen_keys) == {"ABCDEF0123456789ABCDEF0123456789"}


def entries_dates(entries) -> list[str]:
    return [entry.date_hint.isoformat() if entry.date_hint else "" for entry in entries]


def test_configured_api_missing_key_fails_loudly():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>no key here</body></html>")

    with pytest.raises(ListUnavailable) as excinfo:
        OpenApiListAdapter().fetch(_fetcher(handler), _source(), max_pages=1)
    assert "API key" in (excinfo.value.note or "")


def test_configured_api_http_error_raises_instead_of_reporting_zero():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/index.html"):
            return httpx.Response(200, text=LIST_PAGE)
        return httpx.Response(503, text="busy")

    with pytest.raises(ListUnavailable):
        OpenApiListAdapter().fetch(_fetcher(handler), _source(), max_pages=1)


def test_pagination_budget_respects_source_max_pages():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/index.html"):
            return httpx.Response(200, text=LIST_PAGE)
        page = int(request.url.params.get("page", "1"))
        rows = [
            {"title": f"关于第{page}批申报事项的通知", "url": f"https://example.gov.cn/p{page}.html",
             "docDate": "2026-03-01"},
            {"title": f"关于第{page}批资金安排的通知", "url": f"https://example.gov.cn/q{page}.html",
             "docDate": "2026-03-02"},
        ]
        return httpx.Response(200, text=json.dumps({"data": {"resultList": rows}}))

    source = _source(max_pages=1)
    fetch = OpenApiListAdapter().fetch(_fetcher(handler), source, max_pages=5)
    assert fetch.pages_fetched == 1
    assert len(fetch.entries) == 2


def test_list_navigation_titles_are_not_treated_as_documents():
    html = """
    <html><body><ul>
      <li><a href="/xxgk/zfxxgkzn/index.html">政府信息公开</a></li>
      <li><a href="/wzzt/kjxqypy/index.html">科技型企业培育</a></li>
      <li><a href="/zwgk/xxgkml/zcwj/2026/t20260301_1.html">关于印发科技计划管理办法的通知</a></li>
    </ul></body></html>
    """
    entries = extract_list_entries(html, "https://example.gov.cn/zwgk/index.html")
    assert [entry.title for entry in entries] == ["关于印发科技计划管理办法的通知"]
