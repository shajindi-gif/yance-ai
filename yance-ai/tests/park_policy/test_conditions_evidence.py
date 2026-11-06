"""Condition evaluation, eligibility matrix, version and window semantics.

The cases here mirror the failure list in the brief: wrong dates, amount ceilings
mistaken for grants, stale statistics periods, superseded versions, closed windows
being read as repealed policies.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.services.park_policy.conditions import (
    ConditionResult,
    MatrixVerdict,
    amount_display,
    build_matrix,
    evaluate_condition,
)
from app.services.park_policy.evidence import (
    StalenessReason,
    build_window,
    compute_window_state,
    detect_staleness,
    fact_digest,
    group_windows_by_batch,
    resolve_validity,
    superseded_versions,
)


def _cond(**overrides):
    base = {
        "condition_id": "c1",
        "operator": "gte",
        "fact_key": "rd_ratio",
        "expected_value": 3.0,
        "unit": "%",
        "period": "2025",
        "review_status": "confirmed",
        "clause_ref": "第六条（二）",
        "quote": "上年度研发费用占同期销售收入比例不低于3%",
        "char_start": 1024,
        "char_end": 1050,
    }
    base.update(overrides)
    return base


def _fact(value, period="2025", unit=None, status=None):
    payload = {"value": value, "period": period}
    if unit:
        payload["unit"] = unit
    if status:
        payload["status"] = status
    return payload


def test_numeric_threshold_satisfied_with_period_and_unit():
    result = evaluate_condition(_cond(), {"rd_ratio": _fact(4.2, unit="%")})
    assert result.result is ConditionResult.SATISFIED
    assert result.has_locatable_evidence is True


def test_threshold_not_met_is_not_satisfied():
    result = evaluate_condition(_cond(), {"rd_ratio": _fact(1.5, unit="%")})
    assert result.result is ConditionResult.NOT_SATISFIED


def test_missing_fact_is_insufficient_not_false():
    result = evaluate_condition(_cond(), {})
    assert result.result is ConditionResult.INSUFFICIENT
    assert "rd_ratio" in result.note


def test_statistics_period_mismatch_is_needs_review():
    """用 2024 年数据比 2025 年门槛会得出错误的“符合”。"""
    result = evaluate_condition(_cond(), {"rd_ratio": _fact(9.9, period="2024", unit="%")})
    assert result.result is ConditionResult.NEEDS_REVIEW
    assert "统计期间不一致" in result.note


def test_unknown_period_on_fact_is_insufficient():
    result = evaluate_condition(_cond(), {"rd_ratio": {"value": 5.0, "unit": "%"}})
    assert result.result is ConditionResult.INSUFFICIENT
    assert "统计期间" in result.note


def test_unit_mismatch_is_needs_review_not_silent_conversion():
    result = evaluate_condition(_cond(), {"rd_ratio": _fact("4.2万元", unit="万元")})
    assert result.result is ConditionResult.NEEDS_REVIEW
    assert "单位不一致" in result.note


def test_unreviewed_condition_never_yields_satisfied():
    result = evaluate_condition(_cond(review_status="needs_review"), {"rd_ratio": _fact(99.0, unit="%")})
    assert result.result is ConditionResult.NEEDS_REVIEW
    assert result.review_required is True


def test_unsupported_operator_needs_review_instead_of_guessing():
    result = evaluate_condition(_cond(operator="fuzzy_semantic"), {"rd_ratio": _fact(99.0, unit="%")})
    assert result.result is ConditionResult.NEEDS_REVIEW
    assert "无法确定性求值" in result.note


def test_exclusion_condition():
    excluded = _cond(condition_id="c_excl", operator="not_in",
                     fact_key="industry", expected_value=["房地产", "金融"], period=None, unit=None)
    assert evaluate_condition(excluded, {"industry": "房地产"}).result is ConditionResult.NOT_SATISFIED
    assert evaluate_condition(excluded, {"industry": "人工智能"}).result is ConditionResult.SATISFIED


def test_conflicted_fact_needs_client_confirmation():
    result = evaluate_condition(_cond(), {"rd_ratio": _fact(4.2, unit="%", status="conflicted")})
    assert result.result is ConditionResult.NEEDS_REVIEW
    assert "需客户确认" in result.note


def test_amount_ceiling_is_not_reported_as_entitlement():
    """金额上限不得等同于企业能获金额。"""
    cond = {
        "condition_id": "amt", "operator": "lte", "fact_key": "project_investment",
        "expected_value": 500, "unit": "万元", "amount_kind": "entitlement_cap",
    }
    label = amount_display(cond)
    assert "上限" in label
    assert "不等于企业实际可得金额" in label

    unknown_kind = amount_display({**cond, "amount_kind": "unknown"})
    assert "需回原文核对" in unknown_kind


def test_matrix_orders_not_satisfied_above_missing_facts():
    conditions = [
        _cond(condition_id="c_ok"),
        _cond(condition_id="c_fail", expected_value=99.0, fact_key="rd_ratio"),
        _cond(condition_id="c_missing", fact_key="patent_count", unit="件", expected_value=5),
    ]
    matrix = build_matrix(
        policy_id="pol_1",
        policy_version_id="ver_1",
        conditions=conditions,
        facts={"rd_ratio": _fact(4.2, unit="%")},
    )
    assert matrix.verdict is MatrixVerdict.NOT_SATISFIED
    assert "不构成政府认定" in matrix.as_dict()["disclaimer"]


def test_matrix_all_satisfied_is_still_advisory_only():
    matrix = build_matrix(
        policy_id="pol_1",
        policy_version_id="ver_1",
        conditions=[_cond()],
        facts={"rd_ratio": _fact(4.2, unit="%")},
    )
    assert matrix.verdict is MatrixVerdict.LIKELY_SATISFIED
    assert matrix.requires_human_confirmation is True
    assert "likely_satisfied" == str(matrix.verdict)


def test_matrix_scope_block_overrides_conditions():
    matrix = build_matrix(
        policy_id="pol_1",
        policy_version_id="ver_1",
        conditions=[_cond()],
        facts={"rd_ratio": _fact(4.2, unit="%")},
        scope_results=[{"verdict": "not_satisfied", "basis": "scope_type:city"}],
    )
    assert matrix.verdict is MatrixVerdict.NOT_SATISFIED
    assert matrix.blocked_by


def test_window_without_deadline_is_unknown_not_open():
    assert compute_window_state(opens_at="2026-01-01", closes_at=None, today=date(2026, 5, 1)) == "unknown"


def test_window_states():
    today = date(2026, 11, 6)
    assert compute_window_state(opens_at="2026-11-01", closes_at="2026-11-30", today=today) == "open"
    assert compute_window_state(opens_at="2026-12-01", closes_at="2026-12-31", today=today) == "upcoming"
    assert compute_window_state(opens_at="2026-01-01", closes_at="2026-03-31", today=today) == "closed"
    assert compute_window_state(opens_at="2026-01-01", closes_at="2026-12-31", today=today, suspended=True) == "suspended"


def test_batches_are_not_merged_across_years():
    rows = [
        {"window_id": "w2025", "policy_id": "p1", "fiscal_year": 2025, "batch_label": "第一批",
         "opens_at": "2025-03-01", "closes_at": "2025-03-31"},
        {"window_id": "w2026", "policy_id": "p1", "fiscal_year": 2026, "batch_label": "第一批",
         "opens_at": "2026-03-01", "closes_at": "2026-03-31"},
    ]
    grouped = group_windows_by_batch(rows)
    assert len(grouped) == 2

    window = build_window(rows[0], today=date(2026, 11, 6))
    assert window.state == "closed"
    # 窗口已关闭不等于政策已废止。
    assert window.as_dict()["state"] == "closed"


def test_source_anomaly_does_not_repeal_policy():
    versions = [{"policy_id": "p1", "version_id": "v1", "content_hash": "h1",
                 "effective_from": "2025-01-01"}]
    healthy = resolve_validity(versions=versions, source_health="healthy", today=date(2026, 11, 6))
    anomaly = resolve_validity(versions=versions, source_health="source_anomaly", today=date(2026, 11, 6))
    assert healthy.validity == "in_force"
    assert anomaly.validity == "in_force"
    assert "异常不等于政策废止" in anomaly.note


def test_new_version_keeps_old_evidence():
    versions = [
        {"policy_id": "p1", "version_id": "v1", "content_hash": "h1", "effective_from": "2025-01-01"},
        {"policy_id": "p1", "version_id": "v2", "content_hash": "h2", "effective_from": "2026-06-01"},
    ]
    current = resolve_validity(versions=versions, today=date(2026, 11, 6))
    assert current.policy_version_id == "v2"

    superseded = superseded_versions(versions)
    assert superseded[0]["version_id"] == "v1"
    assert superseded[0]["superseded_by"] == "v2"
    assert superseded[0]["preserved"] is True


def test_repeal_document_wins():
    versions = [{"policy_id": "p1", "version_id": "v1", "content_hash": "h1",
                 "effective_from": "2025-01-01"}]
    state = resolve_validity(versions=versions, repeal_document_present=True, today=date(2026, 11, 6))
    assert state.validity == "withdrawn"
    assert state.usable_as_basis is False


def test_expired_policy():
    versions = [{"policy_id": "p1", "version_id": "v1", "content_hash": "h1",
                 "effective_from": "2023-01-01", "effective_to": "2025-12-31"}]
    state = resolve_validity(versions=versions, today=date(2026, 11, 6))
    assert state.validity == "expired"


def test_staleness_detects_version_and_fact_changes():
    current = resolve_validity(
        versions=[{"policy_id": "p1", "version_id": "v2", "content_hash": "h2", "effective_from": "2026-01-01"}],
        today=date(2026, 11, 6),
    )
    facts = {"rd_ratio": _fact(4.2, unit="%")}
    reasons = detect_staleness(
        conclusion={
            "policy_version_id": "v1",
            "policy_version_hash": "h1",
            "fact_digest": "stale",
            "window_state": "open",
            "window_state_now": "closed",
        },
        current=current,
        current_fact_digest=fact_digest(facts),
    )
    assert StalenessReason.POLICY_VERSION_CHANGED in reasons
    assert StalenessReason.FACT_CHANGED in reasons
    assert StalenessReason.WINDOW_CHANGED in reasons


def test_fact_digest_ignores_irrelevant_keys_order():
    a = fact_digest({"a": 1, "b": {"value": 2, "period": "2025"}})
    b = fact_digest({"b": {"value": 2, "period": "2025", "extra": "x"}, "a": 1})
    assert a == b


def test_unknown_boundary_never_used_for_matching_guard():
    from app.services.park_registry.geography import regression_guards

    guards = regression_guards()
    assert guards["park_scope_requires_explicit_park_id"] is True
    assert guards["provincial_scope_requires_city"] is False
