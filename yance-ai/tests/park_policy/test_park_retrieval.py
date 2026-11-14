"""Retrieval-layer regressions: tenant isolation, park scoping, empty-result reasons."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.services.park_policy.retrieval import (
    RetrievalFilters,
    assert_server_side_tenant_filter,
    describe_empty_result,
    extract_document_numbers,
    extract_support_categories,
    normalize_query,
    window_flags,
)


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _StateSession:
    """Minimal stand-in for a Session returning fixed PolicySourceState rows."""

    def __init__(self, states=()):
        self._states = list(states)

    def scalars(self, *_args, **_kwargs):
        return _ScalarResult(self._states)


def test_tenant_is_mandatory_and_fails_closed():
    with pytest.raises(ValueError, match="tenant_id"):
        assert_server_side_tenant_filter(RetrievalFilters(tenant_id=None))


def test_unknown_park_id_is_rejected_not_ignored():
    """把无法解析的 park_id 当"无过滤"会让跨园区政策泄露。"""
    from app.services.park_policy import retrieval as mod

    filters = RetrievalFilters(tenant_id=uuid4(), park_id="park_does_not_exist")
    with pytest.raises(ValueError, match="未知园区"):
        mod._scope_predicates(filters)


def test_no_park_filter_when_park_not_specified():
    filters = RetrievalFilters(tenant_id=uuid4(), province="江苏省", city="苏州市")
    from app.services.park_policy import retrieval as mod

    assert mod._scope_predicates(filters) == []


def test_city_filter_does_not_produce_park_filter():
    """按城市检索不能被解释为按园区检索。"""
    filters = RetrievalFilters(tenant_id=uuid4(), city="苏州市")
    from app.services.park_policy import retrieval as mod

    assert mod._scope_predicates(filters) == []


def test_query_alias_expansion_keeps_trace():
    normalized = normalize_query("专精特新小巨人企业申报条件")
    assert "专精特新“小巨人”" in normalized.canonical
    assert "专精特新" in normalized.matched_aliases
    assert normalized.original == "专精特新小巨人企业申报条件"


def test_institution_rename_is_matched():
    normalized = normalize_query("工信部专项资金")
    assert "工业和信息化部" in normalized.canonical


def test_document_number_is_extracted():
    numbers = extract_document_numbers("国科发高〔2026〕15号 关于组织申报的通知")
    assert len(numbers) == 1
    assert "2026" in numbers[0]


def test_no_document_number_returns_empty():
    assert extract_document_numbers("苏州市研发费用补助政策") == ()


def test_support_category_detection_keeps_designation_separate():
    """认定、认定奖励、贴息、税收优惠必须分别标注。"""
    designation = extract_support_categories("高新技术企业认定")
    assert designation == ("designation",)

    reward = extract_support_categories("首次通过认定给予一次性奖励")
    assert "designation_reward" in reward

    interest = extract_support_categories("贷款贴息支持")
    assert "loan_interest_subsidy" in interest

    tax = extract_support_categories("研发费用加计扣除")
    assert "tax_incentive" in tax


def test_park_catalog_lookup_for_scope_predicate():
    from app.services.park_policy import retrieval as mod

    filters = RetrievalFilters(tenant_id=uuid4(), park_id="park_sz_sip")
    predicates = mod._scope_predicates(filters)
    assert len(predicates) == 1
    assert "park_id" in str(predicates[0]).lower() or "IN" in str(predicates[0]).upper()


def test_window_flags_mark_closed_without_repeal():
    flags = window_flags(
        [
            {"window_id": "w1", "opens_at": "2025-03-01", "closes_at": "2025-03-31"},
            {"window_id": "w2", "opens_at": "2026-11-01", "closes_at": "2026-11-30"},
            {"window_id": "w3", "opens_at": "2026-01-01", "closes_at": None},
        ],
        today=date(2026, 11, 6),
    )
    assert [f["state"] for f in flags] == ["closed", "open", "unknown"]


def test_empty_result_for_city_without_registered_source():
    """未登记来源的城市，空结果不得解释为"确无政策"。"""
    out = describe_empty_result(
        _StateSession(),
        filters=RetrievalFilters(tenant_id=uuid4(), city="佛山市"),
        query="专精特新",
    )
    assert out["reason"] == "source_not_registered"
    assert "不代表没有政策" in out["message"]


def test_empty_result_reports_all_paused():
    class _State:
        def __init__(self, source_id):
            self.source_id = source_id
            self.paused = True
            self.paused_reason = "站点改版"
            self.last_error = None

    from app.services.park_policy.retrieval import _catalog_dir
    from app.services.policy_collection.catalog import load_catalog

    catalog = load_catalog(_catalog_dir())
    zhejiang = [s.source_id for s in catalog.sources if s.province == "浙江省" and s.enabled]
    session = _StateSession([_State(sid) for sid in zhejiang])

    out = describe_empty_result(
        session,
        filters=RetrievalFilters(tenant_id=uuid4(), province="浙江省"),
        query="技改",
    )
    assert out["reason"] == "source_paused"
    assert "站点改版" in out["message"]


def test_empty_result_reports_fetch_failure():
    class _State:
        def __init__(self, source_id):
            self.source_id = source_id
            self.paused = False
            self.paused_reason = None
            self.last_error = "HTTP 429"

    from app.services.park_policy.retrieval import _catalog_dir
    from app.services.policy_collection.catalog import load_catalog

    catalog = load_catalog(_catalog_dir())
    zhejiang = [s.source_id for s in catalog.sources if s.province == "浙江省" and s.enabled]
    session = _StateSession([_State(sid) for sid in zhejiang])

    out = describe_empty_result(
        session,
        filters=RetrievalFilters(tenant_id=uuid4(), province="浙江省"),
        query="技改",
    )
    assert out["reason"] == "fetch_failed"
    assert "确无更新" in out["message"]


def test_empty_result_no_match_keeps_partial_failure_visible():
    """部分来源失败时不能简单说"确无更新"。"""
    class _State:
        def __init__(self, source_id, error=None):
            self.source_id = source_id
            self.paused = False
            self.paused_reason = None
            self.last_error = error

    from app.services.park_policy.retrieval import _catalog_dir
    from app.services.policy_collection.catalog import load_catalog

    catalog = load_catalog(_catalog_dir())
    zhejiang = [s.source_id for s in catalog.sources if s.province == "浙江省" and s.enabled]
    assert len(zhejiang) >= 2
    states = [_State(sid) for sid in zhejiang]
    states[0].last_error = "timeout"
    out = describe_empty_result(
        _StateSession(states),
        filters=RetrievalFilters(tenant_id=uuid4(), province="浙江省"),
        query="技改",
    )
    assert out["reason"] == "no_match"
    assert out["sources_failing"] == [zhejiang[0]]
