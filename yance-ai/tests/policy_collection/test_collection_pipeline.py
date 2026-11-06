"""Acceptance tests for the continuous policy collection pipeline.

These tests use ``MemoryPolicyStore`` and a scripted httpx transport, so they run
without PostgreSQL and without touching any live government site.  Real-site
verification lives in ``scripts/policy_collection/cli.py verify`` and is recorded
in ``docs/policy-collection-test-report.md`` — a synthetic fixture here must not
be reported as real source coverage.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from app.services.policy_collection.catalog import SourceDefinition, load_catalog
from app.services.policy_collection.classify import classify
from app.services.policy_collection.extract import (
    detect_client_redirect,
    extract_document_page,
    extract_list_entries,
    parse_cn_date,
)
from app.services.policy_collection.fetch import SafeFetcher
from app.services.policy_collection.fingerprint import (
    ChangeKind,
    ExistingState,
    IncomingDocument,
    batch_signature,
    decide_change,
)
from app.services.policy_collection.rawstore import RawEvidenceStore
from app.services.policy_collection.store import (
    DocumentPayload,
    MemoryPolicyStore,
    WindowPayload,
    jurisdiction_for,
)
from app.services.policy_collection.urlguard import (
    ResolutionError,
    TargetPolicy,
    UnsafeURLError,
)

CATALOG_DIR = Path("config/policy_sources")


def _source(**overrides) -> SourceDefinition:
    base = dict(
        source_id="test_source",
        name="测试来源",
        authority="测试机构",
        level="provincial",
        province="浙江省",
        city=None,
        channel="policy_document",
        entry_url="https://example.gov.cn/col/index.html",
        allowed_domains=("example.gov.cn",),
        adapter="generic_list",
        enabled=True,
        verification_state="reachable",
    )
    base.update(overrides)
    return SourceDefinition(**base)


def _payload(source: SourceDefinition, *, text: str, url: str, title: str = "通知") -> DocumentPayload:
    return DocumentPayload(
        source=source,
        run_id=None,
        url=url,
        requested_url=url,
        title=title,
        text=text,
        classification=classify(title, text),
        published_at=date(2026, 3, 1),
    )


# --------------------------------------------------------------------------- #
# 1. idempotency and versioning
# --------------------------------------------------------------------------- #
def test_rerun_same_document_is_idempotent():
    store = MemoryPolicyStore()
    source = _source()
    payload = _payload(source, text="第一条正文内容，用于测试幂等。", url="https://example.gov.cn/a.html")
    first = store.save_document(payload)
    second = store.save_document(payload)
    assert first.change == "new"
    assert second.change in {"unchanged", "repost_updated"}
    assert len(store.records) == 1
    assert len(store._versions) == 1


def test_same_url_new_content_creates_version_and_keeps_old():
    store = MemoryPolicyStore()
    source = _source()
    url = "https://example.gov.cn/a.html"
    store.save_document(_payload(source, text="原始正文：补助 100 万元。", url=url))
    second = store.save_document(_payload(source, text="更正后正文：补助 80 万元。", url=url))
    assert second.change == "new_version"
    assert second.version == 2
    versions = store._versions[str(second.policy_id)]
    assert len(versions) == 2, "old evidence must be retained"


def test_repost_from_other_source_is_linked_not_merged():
    store = MemoryPolicyStore()
    primary = _source(source_id="s1", province="浙江省")
    mirror = _source(
        source_id="s2",
        province="杭州市",
        level="municipal",
        city="杭州市",
        entry_url="https://example.gov.cn/hz/index.html",
    )
    text = "浙江省科学技术厅关于组织申报重点研发计划的通知。"
    first = store.save_document(
        _payload(primary, text=text, url="https://example.gov.cn/art/1.html",
                 title="关于组织申报重点研发计划的通知")
    )
    second = store.save_document(
        _payload(mirror, text=text, url="https://example.gov.cn/art/2.html",
                 title="关于组织申报重点研发计划的通知")
    )
    assert second.change.startswith("repost")
    assert len(store.records) == 1, "same document must not duplicate"
    assert first.policy_id == second.policy_id


def test_distinct_application_rounds_are_not_merged():
    store = MemoryPolicyStore()
    source = _source()
    url = "https://example.gov.cn/a.html"
    text = "申报条件如下。"
    first = store.save_document(
        _payload(source, text=text, url=url, title="2025年度第一批申报通知")
    )
    second = store.save_document(
        _payload(source, text=text, url=url, title="2026年度第二批申报通知")
    )
    assert first.policy_id != second.policy_id


# --------------------------------------------------------------------------- #
# 2. jurisdiction correctness
# --------------------------------------------------------------------------- #
def test_provincial_scope_is_not_narrowed_to_capital():
    source = _source(level="provincial", province="浙江省", city=None)
    assert jurisdiction_for(source) == "浙江省"


def test_municipal_scope_is_city_level():
    source = _source(level="municipal", province="广东省", city="深圳市")
    assert jurisdiction_for(source) == "广东省深圳市"


def test_national_scope():
    assert jurisdiction_for(_source(level="national", province=None)) == "全国"


def test_jurisdiction_never_derived_from_title_text():
    """A Hangzhou-authored provincial notice stays provincial."""
    source = _source(level="provincial", province="浙江省")
    payload = _payload(
        source,
        text="发文单位地址：杭州市西湖区。",
        url="https://example.gov.cn/b.html",
        title="浙江省科技厅关于杭州市试点工作的通知",
    )
    store = MemoryPolicyStore()
    store.save_document(payload)
    assert payload.source.province == "浙江省"
    assert payload.source.city is None


# --------------------------------------------------------------------------- #
# 3. dates, windows, amounts
# --------------------------------------------------------------------------- #
def test_list_navigation_dates_are_not_taken_as_publish_dates():
    html = """
    <ul><li><span>2026-11-05</span><a href="/art/1.html">关于申报2026年度项目的通知</a></li></ul>
    """
    entries = extract_list_entries(html, "https://example.gov.cn/list/index.html")
    assert len(entries) == 1
    assert entries[0].date_hint == date(2026, 11, 5)


def test_implausible_publish_date_is_rejected():
    assert parse_cn_date("2026-13-45") is None
    assert parse_cn_date("1999-01-01") is None


def test_multiple_application_windows_stay_separate():
    text = (
        "第一批申报时间：2026年3月1日至2026年3月31日。"
        "第二批申报时间：2026年9月1日至2026年9月30日。"
    )
    classification = classify("2026年度项目申报通知", text)
    windows = classification.application_windows
    assert len(windows) >= 2
    ends = {window.end for window in windows if window.end}
    assert date(2026, 3, 31) in ends
    assert date(2026, 9, 30) in ends


def test_recognised_award_is_not_reported_as_cash_subsidy():
    classification = classify(
        "关于公布2026年度高新技术企业名单的通知",
        "经审核，认定下列企业为高新技术企业，颁发证书。",
    )
    forms = {finding.form for finding in classification.support_forms}
    assert "qualification" in forms
    assert "project_grant" not in forms, "a designation must not be reported as money"


def test_missing_amount_stays_unknown():
    classification = classify("关于组织申报的通知", "有关事项通知如下，请按要求报送材料。")
    assert all(finding.amount_text in (None, "") for finding in classification.support_forms) or (
        not classification.support_forms
    )


def test_expired_and_extended_notices_are_classified_differently():
    extended = classify("关于延长2026年度项目申报期限的通知", "申报截止时间延长至2026年12月31日。")
    withdrawn = classify("关于废止有关文件的通知", "经研究，决定废止下列文件。")
    assert extended.doc_kind in {"extension", "application_notice", "notice", "other"}
    assert withdrawn.doc_kind in {"repeal", "notice", "other"}
    assert extended.doc_kind != withdrawn.doc_kind


# --------------------------------------------------------------------------- #
# 4. fetch safety
# --------------------------------------------------------------------------- #
def _fetcher(handler, **kwargs) -> SafeFetcher:
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return SafeFetcher(
        client=client,
        target_policy=TargetPolicy(
            allowed_domains=("example.gov.cn",),
            resolver=lambda _host: ["93.184.216.34"],
        ),
        min_interval_seconds=0,
        sleeper=lambda _s: None,
        **kwargs,
    )


def test_robots_disallow_blocks_request():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /col/\n")
        return httpx.Response(200, text="<html>should not be fetched</html>")

    result = _fetcher(handler).get("https://example.gov.cn/col/index.html", purpose="list")
    assert result.robots_denied is True
    assert not result.ok


def test_robots_allow_path():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html>ok</html>")

    result = _fetcher(handler).get("https://example.gov.cn/col/index.html", purpose="list")
    assert result.ok


def test_429_is_retried_then_reported():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "0"})

    result = _fetcher(handler, max_retries=1).get("https://example.gov.cn/a.html")
    assert not result.ok
    assert result.status_code == 429
    assert calls["n"] >= 2, "must retry with backoff, not hammer"


def test_timeout_is_reported_not_raised():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        raise httpx.ReadTimeout("slow site", request=request)

    result = _fetcher(handler).get("https://example.gov.cn/a.html")
    assert not result.ok
    assert result.error_kind in {"timeout", "network"}


def test_redirect_to_internal_address_is_blocked():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/a.html":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})
        return httpx.Response(200, text="internal")

    result = _fetcher(handler).get("https://example.gov.cn/a.html")
    assert not result.ok
    assert result.error_kind == "blocked"


def test_dns_failure_is_reported_as_network_not_block():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, text="unreachable")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = SafeFetcher(
        client=client,
        target_policy=TargetPolicy(
            allowed_domains=("no-such-host.invalid",),
            resolver=lambda host: (_ for _ in ()).throw(ResolutionError(f"dns resolution failed: {host}")),
        ),
        min_interval_seconds=0,
        sleeper=lambda _s: None,
    )
    result = fetcher.get("https://no-such-host.invalid/a.html")
    assert not result.ok
    assert result.error_kind == "network"


def test_cloud_metadata_endpoint_is_blocked():
    policy = TargetPolicy(allowed_domains=("169.254.169.254",))
    with pytest.raises(UnsafeURLError):
        policy.check("http://169.254.169.254/latest/meta-data/")


def test_oversized_response_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=b"x" * (2 * 1024 * 1024))

    result = _fetcher(handler, max_bytes=64 * 1024).get("https://example.gov.cn/a.html")
    assert not result.ok
    assert result.error_kind == "too_large"
    # Rejected on the declared Content-Length: nothing is buffered in memory.
    assert not result.content


# --------------------------------------------------------------------------- #
# 5. change detection
# --------------------------------------------------------------------------- #
def test_decide_change_new_when_no_existing():
    incoming = IncomingDocument(
        final_url="https://example.gov.cn/a.html",
        content_sha256="sha-new",
        title="通知",
        doc_number=None,
        issuer="测试机构",
    )
    assert decide_change(None, incoming) is ChangeKind.NEW


def test_decide_change_unchanged_when_hash_matches():
    digest = hashlib.sha256(b"same").hexdigest()
    existing = ExistingState(
        document_id=None,
        final_url="https://example.gov.cn/a.html",
        content_sha256=digest,
        title="通知",
        doc_number=None,
        issuer=None,
    )
    same = IncomingDocument(
        final_url="https://example.gov.cn/a.html",
        content_sha256=digest,
        title="通知",
        doc_number=None,
        issuer=None,
    )
    changed = IncomingDocument(
        final_url="https://example.gov.cn/a.html",
        content_sha256="different-hash",
        title="通知",
        doc_number=None,
        issuer=None,
    )
    assert decide_change(existing, same) is ChangeKind.UNCHANGED
    assert decide_change(existing, changed) is ChangeKind.NEW_VERSION


def test_batch_signature_separates_rounds():
    assert batch_signature("2025年度第一批申报通知") != batch_signature("2026年度第二批申报通知")
    assert batch_signature("关于组织申报的通知") == ()


# --------------------------------------------------------------------------- #
# 6. evidence storage and parsing
# --------------------------------------------------------------------------- #
def test_raw_evidence_store_is_content_addressed_and_never_overwrites(tmp_path):
    store = RawEvidenceStore(tmp_path)
    body = b"<html>policy</html>"
    when = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    first = store.save(
        source_id="s1",
        url="https://example.gov.cn/a.html",
        payload=body,
        content_type="text/html",
        fetched_at=when,
    )
    second = store.save(
        source_id="s1",
        url="https://example.gov.cn/a.html",
        payload=body,
        content_type="text/html",
        fetched_at=when,
    )
    assert first.path == second.path
    assert second.reused is True
    assert Path(first.path).exists()
    assert hashlib.sha256(body).hexdigest() in Path(first.path).name
    # A changed body must land in a different object, never overwrite evidence.
    third = store.save(
        source_id="s1",
        url="https://example.gov.cn/a.html",
        payload=b"<html>revised</html>",
        content_type="text/html",
        fetched_at=when,
    )
    assert third.path != first.path
    assert store.read(first.path) == body


def test_extract_document_page_pulls_text_and_attachments():
    html = """
    <html><head><title>关于组织申报2026年度重点研发计划的通知</title></head><body>
    <h1>关于组织申报2026年度重点研发计划的通知</h1>
    <div class="xxgk">发文机构：浙江省科学技术厅</div>
    <p>申报截止时间为2026年3月31日。</p>
    <a href="/files/guide.pdf">附件1：申报指南.pdf</a>
    <a href="/files/form.docx">附件2：申报书.docx</a>
    </body></html>
    """
    page = extract_document_page(html, "https://example.gov.cn/art/1.html")
    assert "重点研发计划" in page.title
    assert "2026年3月31日" in page.text
    assert len(page.attachments) == 2
    assert page.attachments[0].url.startswith("https://example.gov.cn/files/")


# --------------------------------------------------------------------------- #
# 7. catalogue contract
# --------------------------------------------------------------------------- #
def test_catalog_loads_and_validates():
    catalog = load_catalog(CATALOG_DIR)
    assert catalog.validate() == []
    assert len(catalog.cities) == 30
    coverage = catalog.coverage()
    assert coverage["provincial_divisions_registered"] == 31
    assert coverage["national_sources"] >= 10


def test_catalog_never_duplicates_municipality_sources():
    catalog = load_catalog(CATALOG_DIR)
    seen: dict[str, str] = {}
    for source in catalog.sources:
        key = source.canonical_entry_url
        if source.shared_jurisdiction:
            assert key not in seen, f"shared source double-registered: {source.source_id}"
        seen.setdefault(key, source.source_id)


def test_every_enabled_source_has_allowed_domains_and_interval():
    catalog = load_catalog(CATALOG_DIR)
    for source in catalog.enabled_sources:
        assert source.allowed_domains, source.source_id
        assert source.check_interval_hours > 0
        assert source.entry_url.startswith(("http://", "https://"))


def test_priority_cities_are_flagged_as_first_batch_not_official_ranking():
    catalog = load_catalog(CATALOG_DIR)
    blob = " ".join(
        [*(catalog.notes or " ").split(), *(reason for city in catalog.cities for reason in city.reasons)]
    )
    assert "首批" in blob or "first batch" in blob.lower()
    for city in catalog.cities:
        assert city.year, f"{city.city} missing data year"
        assert city.data_sources, f"{city.city} missing data sources"


# --------------------------------------------------------------------------- #
# 8. tenant isolation
# --------------------------------------------------------------------------- #
def test_public_policy_payloads_carry_no_tenant_id():
    source = _source()
    payload = _payload(source, text="公开政策正文。", url="https://example.gov.cn/c.html")
    assert not hasattr(payload, "tenant_id")


def test_memory_store_has_no_tenant_dimension():
    store = MemoryPolicyStore()
    store.save_document(
        _payload(_source(), text="正文。", url="https://example.gov.cn/d.html")
    )
    record = store.records[0]
    assert not hasattr(record, "tenant_id")


# --------------------------------------------------------------------------- #
# 9. windows are independent of the policy row
# --------------------------------------------------------------------------- #
def test_window_payload_keeps_its_own_dates():
    window = WindowPayload(
        label="第一批",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        entry_url="https://example.gov.cn/apply",
    )
    assert window.end_date == date(2026, 3, 31)
    assert window.entry_url.endswith("/apply")


# --------------------------------------------------------------------------- #
# 10. client-side redirect shells
# --------------------------------------------------------------------------- #
def test_js_redirect_shell_is_detected_despite_cms_scripts():
    """A shell page drags in the whole CMS bundle; that must not hide the redirect."""
    html = (
        "<html><head>"
        '<script src="/cms_files/jquery.js"></script>'
        "<script>" + "var padding = 1;" * 60 + "</script>"
        "</head><body>"
        '<script>window.location.href="/search/wjfb.html?category=51"</script>'
        "</body></html>"
    )
    assert (
        detect_client_redirect(html, "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html")
        == "https://www.miit.gov.cn/search/wjfb.html?category=51"
    )


def test_real_content_page_is_never_treated_as_redirect_shell():
    """A substantive page that merely mentions location.href in JS stays put."""
    body = "".join(f'<li><a href="/art/{i}.html">文件标题第{i}号发布通知</a></li>' for i in range(8))
    html = f"<html><body><ul>{body}</ul><script>location.href='/x'</script></body></html>"
    assert detect_client_redirect(html, "https://example.gov.cn/list/index.html") is None
