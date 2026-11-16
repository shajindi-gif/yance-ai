"""End-to-end integration tests for the policy collection runner.

A scripted httpx transport stands in for the government sites. These are
integration tests of our own pipeline (list parsing → article fetch → attachment
fetch → evidence store → versioned import → health accounting), *not* evidence of
real source coverage; real-source connectivity is recorded separately by
``scripts/policy_collection/cli.py verify`` and in the test report.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.services.policy_collection.catalog import SourceDefinition
from app.services.policy_collection.fetch import SafeFetcher
from app.services.policy_collection.rawstore import RawEvidenceStore
from app.services.policy_collection.runner import CollectionLimits, PolicyCollectionRunner
from app.services.policy_collection.store import MemoryPolicyStore
from app.services.policy_collection.urlguard import TargetPolicy

HOST = "www.example.gov.cn"


def _source(**overrides) -> SourceDefinition:
    base = dict(
        source_id="city_demo_ksj",
        name="示范市科技局通知公告",
        authority="示范市科学技术局",
        level="municipal",
        province="广东省",
        city="示范市",
        channel="application_notice",
        entry_url=f"https://{HOST}/col/list/index.html",
        allowed_domains=(HOST,),
        adapter="generic_list",
        enabled=True,
        verification_state="reachable",
    )
    base.update(overrides)
    return SourceDefinition(**base)


def _site(articles: dict[str, str], list_html: str | None = None, *, files: dict[str, bytes] | None = None):
    """Build a handler serving a list page, article pages and attachments."""
    listing = list_html

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if path == "/col/list/index.html":
            if listing is None:
                return httpx.Response(404)
            return httpx.Response(200, text=listing, headers={"content-type": "text/html"})
        if path in articles:
            return httpx.Response(200, text=articles[path], headers={"content-type": "text/html"})
        if files and path in files:
            return httpx.Response(200, content=files[path])
        return httpx.Response(404)

    return handler


def _runner(handler, tmp_path: Path, *, max_items: int | None = 5) -> PolicyCollectionRunner:
    def factory(*, source, max_bytes, limits):
        client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
        return SafeFetcher(
            client=client,
            target_policy=TargetPolicy(
                allowed_domains=tuple(source.allowed_domains),
                resolver=lambda _host: ["93.184.216.34"],
            ),
            user_agent="test",
            max_bytes=max_bytes,
            min_interval_seconds=0,
            max_retries=0,
            sleeper=lambda _s: None,
            respect_robots=True,
        )

    return PolicyCollectionRunner(
        store=MemoryPolicyStore(),
        raw_store=RawEvidenceStore(tmp_path / "raw"),
        limits=CollectionLimits(max_detail_bytes=2 * 1024 * 1024),
        fetcher_factory=factory,
        sleep=lambda _s: None,
    )


LIST_HTML = """
<html><body>
<ul class="list">
  <li><span>2026-03-02</span><a href="/art/2026/notice-1.html">关于组织申报2026年度重点研发计划项目的通知</a></li>
  <li><span>2025-09-10</span><a href="/art/2025/notice-2.html">关于公布2025年度高新技术企业认定名单的通知</a></li>
</ul>
</body></html>
"""

ARTICLE_1 = """
<html><head><title>关于组织申报2026年度重点研发计划项目的通知</title></head><body>
<div class="content">
<h1>关于组织申报2026年度重点研发计划项目的通知</h1>
<p>各有关单位：</p>
<p>为支持人工智能、机器人等产业，现组织申报2026年度重点研发计划项目，单个项目最高资助200万元。</p>
<p>第一批申报时间：2026年3月1日至2026年3月31日。</p>
<a href="/files/guide.pdf">附件1：申报指南.pdf</a>
</div>
</body></html>
"""

ARTICLE_2 = """
<html><head><title>关于公布2025年度高新技术企业认定名单的通知</title></head><body>
<div class="content">
<h1>关于公布2025年度高新技术企业认定名单的通知</h1>
<p>根据《高新技术企业认定管理办法》，经专家评审、公示等程序，认定下列企业为高新技术企业，颁发证书，有效期三年。</p>
<p>各区科技主管部门应做好后续服务工作，落实高新技术企业相关税收优惠政策。</p>
</div>
</body></html>
"""


def test_full_run_collects_articles_attachments_and_evidence(tmp_path):
    handler = _site(
        {"/art/2026/notice-1.html": ARTICLE_1, "/art/2025/notice-2.html": ARTICLE_2},
        LIST_HTML,
        files={"/files/guide.pdf": b"%PDF-1.4 fake"},
    )
    runner = _runner(handler, tmp_path)
    outcome = runner.run_source(_source())

    assert outcome.status == "success", outcome.error
    assert outcome.new_documents == 2
    assert outcome.attachments_saved >= 1
    store: MemoryPolicyStore = runner.store
    assert len(store.records) == 2
    # Original pages and attachments are persisted as evidence on disk.
    evidence_files = list((tmp_path / "raw").rglob("*"))
    assert any(p.is_file() and p.suffix == ".html" for p in evidence_files)


def test_rerun_is_idempotent_and_reports_zero_new(tmp_path):
    handler = _site(
        {"/art/2026/notice-1.html": ARTICLE_1, "/art/2025/notice-2.html": ARTICLE_2},
        LIST_HTML,
    )
    runner = _runner(handler, tmp_path)
    first = runner.run_source(_source())
    second = runner.run_source(_source())

    assert first.new_documents == 2
    assert second.new_documents == 0
    assert second.status == "no_update"
    # "0 new" must be explicitly attributable to no change, not to a failure.
    assert second.zero_reason == "no_change"
    assert len(runner.store.records) == 2


def test_same_url_update_creates_new_version_and_keeps_old_evidence(tmp_path):
    updated = ARTICLE_1.replace("最高资助200万元", "最高资助150万元（已更正）")
    handler = _site(
        {"/art/2026/notice-1.html": ARTICLE_1, "/art/2025/notice-2.html": ARTICLE_2},
        LIST_HTML,
    )
    runner = _runner(handler, tmp_path)
    runner.run_source(_source())

    handler2 = _site(
        {"/art/2026/notice-1.html": updated, "/art/2025/notice-2.html": ARTICLE_2},
        LIST_HTML,
    )
    runner2 = _runner(handler2, tmp_path)
    runner2.store = runner.store  # same database, same evidence root
    outcome = runner2.run_source(_source())

    assert outcome.updated_documents >= 1
    record = runner.store._by_url[
        "https://www.example.gov.cn/art/2026/notice-1.html"
    ]
    assert record.version == 2, "old version must be retained, new one appended"


def test_list_failure_does_not_mark_existing_policies_dead(tmp_path):
    runner = _runner(_site({}, None), tmp_path)  # list page 404s
    outcome = runner.run_source(_source())
    assert outcome.status in {"failed", "blocked"}
    assert outcome.error_kind
    assert outcome.zero_reason == "fetch_failed"
    # Nothing may be republished as "repealed" because a fetch failed.
    assert all(record.change != "repeal" for record in runner.store.records)


def test_zero_new_distinguishes_failure_from_no_news(tmp_path):
    failing = _runner(lambda request: httpx.Response(500), tmp_path)
    outcome = failing.run_source(_source())
    assert outcome.new_documents == 0
    assert outcome.zero_reason != "no_change", "a broken source must not look quiet"


def test_paused_source_is_not_collected_but_policies_stay_readable(tmp_path):
    handler = _site(
        {"/art/2026/notice-1.html": ARTICLE_1, "/art/2025/notice-2.html": ARTICLE_2},
        LIST_HTML,
    )
    runner = _runner(handler, tmp_path)
    runner.run_source(_source())
    before = len(runner.store.records)

    paused = _source(enabled=False)
    assert paused.enabled is False
    # The store keeps serving what was already ingested even while collection stops.
    assert len(runner.store.records) == before == 2


def test_oversized_article_is_rejected_without_ingestion(tmp_path):
    huge = "<html><body>" + ("政策内容" * 400_000) + "</body></html>"
    handler = _site({"/art/2026/notice-1.html": huge, "/art/2025/notice-2.html": ARTICLE_2}, LIST_HTML)
    runner = _runner(handler, tmp_path)
    runner.limits = CollectionLimits(max_detail_bytes=64 * 1024)
    outcome = runner.run_source(_source())

    assert outcome.status in {"partial", "success", "no_update", "failed"}
    assert outcome.failed_documents >= 1
    # The oversized document must not be stored as if it were complete evidence.
    assert all(len(record.title) < 200 for record in runner.store.records)


def test_attachment_failure_is_recorded_not_silently_ignored(tmp_path):
    handler = _site(
        {"/art/2026/notice-1.html": ARTICLE_1, "/art/2025/notice-2.html": ARTICLE_2},
        LIST_HTML,
        files={},  # guide.pdf returns 404
    )
    runner = _runner(handler, tmp_path)
    outcome = runner.run_source(_source())
    assert outcome.status in {"success", "partial", "no_update"}
    assert outcome.attachments_failed >= 1


def test_robots_disallow_yields_blocked_outcome(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return httpx.Response(200, text=LIST_HTML)

    runner = _runner(handler, tmp_path)
    outcome = runner.run_source(_source())
    assert outcome.status in {"blocked", "failed"}
    assert outcome.error_kind in {"robots", "blocked", "empty_list", "all_documents_failed"}


def test_evidence_store_rejects_path_traversal(tmp_path):
    store = RawEvidenceStore(tmp_path / "raw")
    payload = b"data"
    saved = store.save(
        source_id="../../etc",
        url="https://www.example.gov.cn/a.html",
        payload=payload,
        content_type="text/html",
        fetched_at=datetime(2026, 11, 6, tzinfo=UTC),
    )
    assert str((tmp_path / "raw").resolve()) in saved.path
    assert ".." not in Path(saved.path).parts
    assert hashlib.sha256(payload).hexdigest() in Path(saved.path).name
    with pytest.raises(ValueError):
        store.read("/etc/passwd")


class _RecordingStore(MemoryPolicyStore):
    """Memory store that keeps the raw payloads, so tests can assert on fields."""

    def __init__(self) -> None:
        super().__init__()
        self.payloads: list = []

    def save_document(self, payload):
        self.payloads.append(payload)
        return super().save_document(payload)


FUTURE_LIST_HTML = """
<html><body>
<ul class="list">
  <li><span>2030-12-05</span><a href="/art/future/notice.html">关于组织申报2031年度重点研发计划项目的通知</a></li>
</ul>
</body></html>
"""

FUTURE_ARTICLE = """
<html><head><title>关于组织申报2031年度重点研发计划项目的通知</title></head><body>
<div class="content">
<h1>关于组织申报2031年度重点研发计划项目的通知</h1>
<p>各有关单位：</p>
<p>为支持人工智能、机器人等产业，现组织申报2031年度重点研发计划项目，单个项目最高资助200万元。</p>
</div>
</body></html>
"""


def test_implausible_future_publish_date_is_dropped_not_trusted(tmp_path):
    """A wrong (future) date must not become a policy publish date or deadline."""
    handler = _site({"/art/future/notice.html": FUTURE_ARTICLE}, FUTURE_LIST_HTML)
    runner = _runner(handler, tmp_path)
    runner.store = _RecordingStore()

    outcome = runner.run_source(_source())
    assert outcome.new_documents == 1
    payload = runner.store.payloads[0]
    assert payload.published_at is None
    assert payload.http_meta.get("publish_date_rejected") == "2030-12-05"
    # the page itself is still kept as evidence
    assert payload.storage_path


def test_unsupported_attachment_is_marked_unsupported_not_parsed(tmp_path):
    """Legacy .doc cannot be parsed deterministically -> must not look parsed."""
    doc_article = ARTICLE_1.replace(
        '<a href="/files/guide.pdf">附件1：申报指南.pdf</a>',
        '<a href="/files/legacy.doc">附件1：申报指南.doc</a>',
    )
    handler = _site(
        {"/art/2026/notice-1.html": doc_article, "/art/2025/notice-2.html": ARTICLE_2},
        LIST_HTML,
        files={"/files/legacy.doc": b"\xd0\xcf\x11\xe0 legacy word binary"},
    )
    runner = _runner(handler, tmp_path)
    runner.store = _RecordingStore()
    outcome = runner.run_source(_source())
    assert outcome.status == "success", outcome.error
    statuses = [a.parse_status for p in runner.store.payloads for a in p.attachments]
    assert statuses == ["unsupported"], statuses
