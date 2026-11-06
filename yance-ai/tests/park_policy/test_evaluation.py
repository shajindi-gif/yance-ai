"""Evaluation harness regressions — the harness itself must not flatter the system."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.park_policy import evaluation as ev


@pytest.fixture(scope="module")
def eval_set():
    return ev.load_eval_set()


def test_eval_set_loads_and_validates(eval_set):
    assert ev.validate_eval_set(eval_set) == []
    assert eval_set.version.startswith("2026-11-06")
    assert len(eval_set.tasks) >= 20
    assert {"engineering", "retrieval", "eligibility"} <= set(eval_set.suites())


def test_every_task_declares_prohibited_even_if_not_high_severity(eval_set):
    missing = [t.task_id for t in eval_set.tasks if not t.prohibited]
    assert missing == [], f"缺少 prohibited 的任务: {missing}"


def test_no_policy_family_spans_two_splits(eval_set):
    """同一政策家族出现在 dev 与 test 会导致改写泄漏。"""
    families: dict[str, set[str]] = {}
    for task in eval_set.tasks:
        for family in task.policy_families:
            families.setdefault(family, set()).add(task.split)
    leaked = {k: v for k, v in families.items() if len(v) > 1}
    assert leaked == {}


def test_validation_catches_family_leak(tmp_path):
    payload = (ev.EVAL_DIR / "park_policy_eval_v1.yaml").read_text(encoding="utf-8")
    broken = payload.replace(
        "  - id: ENG-GEO-001\n    suite: engineering\n    split: test",
        "  - id: ENG-GEO-001\n    suite: engineering\n    split: dev",
    )
    target = tmp_path / "broken.yaml"
    target.write_text(broken, encoding="utf-8")
    problems = ev.validate_eval_set(ev.load_eval_set(target))
    assert any("评测泄漏" in p for p in problems)


def test_validation_catches_duplicate_id(tmp_path):
    payload = (ev.EVAL_DIR / "park_policy_eval_v1.yaml").read_text(encoding="utf-8")
    broken = payload.replace("- id: ENG-GEO-002", "- id: ENG-GEO-001", 1)
    target = tmp_path / "dup.yaml"
    target.write_text(broken, encoding="utf-8")
    problems = ev.validate_eval_set(ev.load_eval_set(target))
    assert any("重复任务ID" in p for p in problems)


def test_rule_baseline_scopes_to_engineering_suite(eval_set):
    """规则基线不得对真实政策题作答。"""
    for task in eval_set.tasks:
        if task.suite == "engineering":
            continue
        answer = ev._rule_baseline(task)
        assert answer.behavior == "insufficient_evidence"
        assert answer.claims == ()


def test_naive_arm_is_punished_as_severe(eval_set):
    """过度声明的基线必须在严重错误上被打出来，而不是看起来还行。"""
    result = ev.run_arm(
        eval_set,
        ev.ArmSpec(name="floor", describe={}, runnable=True),
        ev._naive_lexical_arm,
    )
    eng = result["by_suite"]["engineering"]
    assert eng["severe_error_rate"] is not None
    assert eng["severe_error_rate"] > 0.5


def test_rule_baseline_has_no_severe_errors_on_engineering(eval_set):
    result = ev.run_arm(eval_set, ev.describe_arm_c(), ev._rule_baseline)
    eng = result["by_suite"]["engineering"]
    assert eng["severe_error_count"] == 0, [
        r for r in result["tasks"] if r["severe_error"]
    ]
    assert eng["behavior_match_rate"] == 1.0


def test_report_refuses_single_headline_score(eval_set):
    report = ev.build_report(eval_set)
    assert report["conclusion"]["business_quality"] == "insufficient"
    assert "不得用于证明业务准确率" in report["conclusion"]["statement"]


def test_model_arms_are_blocked_not_simulated(eval_set):
    report = ev.build_report(eval_set)
    arms = {a["name"]: a for a in report["arms"]}
    assert arms["A_general_model"]["runnable"] is False
    assert arms["B_same_model_with_corpus"]["runnable"] is False
    for name in ("A_general_model", "B_same_model_with_corpus"):
        assert arms[name]["result"] is None
        assert "禁止" in arms[name]["blocked_reason"] or "预算" in arms[name]["blocked_reason"]


def test_blocked_suites_are_declared(eval_set):
    report = ev.build_report(eval_set)
    assert set(report["conclusion"]["blocked_suites"]) == {"retrieval", "eligibility"}


def test_report_is_reproducible_across_runs(eval_set):
    first = ev.build_report(eval_set)
    second = ev.build_report(eval_set)
    assert first["eval_set_digest"] == second["eval_set_digest"]
    assert first["arms"][2]["result"] == second["arms"][2]["result"]


def test_write_report_creates_file(eval_set, tmp_path):
    report = ev.build_report(eval_set)
    path = ev.write_report(report, tmp_path / "report.json")
    assert path.exists()
    assert '"business_quality": "insufficient"' in path.read_text(encoding="utf-8")
