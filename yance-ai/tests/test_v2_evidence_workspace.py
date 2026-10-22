"""Synthetic source-binding regressions, not business quality labels."""

from types import SimpleNamespace as Row
from uuid import uuid4

import pytest

from app.services.applications.artifacts import content_checksum
from app.services.applications.workspace import (
    artifact_source_state,
    evidence_matrix,
    qualification_source_issues,
    readiness,
    workspace_fingerprint,
)


def records(status="POTENTIALLY_ELIGIBLE"):
    return {
        "requirements": [],
        "evidence": [
            Row(
                id=uuid4(),
                verified=True,
                eligibility_rule_id=uuid4(),
                quote="合成条款",
                source_url="https://example.invalid",
                article="第一条",
            )
        ],
        "links": [],
        "eligibility": Row(
            id=uuid4(),
            status=status,
            criteria_json=[],
            missing_information_json=[],
            profile_version_id=uuid4(),
        ),
        "context_issues": [],
    }


@pytest.mark.parametrize(
    "status", ["REQUIRES_REVIEW", "UNRECOGNIZED", "NEED_MORE_INFORMATION", "NOT_ELIGIBLE"]
)
def test_unknown_or_review_eligibility_cannot_be_ready(status):
    assert not readiness(records(status))["can_submit_for_review"]


def test_policy_context_blocks_readiness_even_with_verified_quote():
    r = records()
    r["context_issues"] = ["政策已撤回"]
    assert not readiness(r)["can_submit_for_review"]


def test_snapshot_detects_changed_inputs():
    r = records()
    original = workspace_fingerprint(r)
    r["requirements"] = [Row(id=uuid4(), status="missing")]
    assert workspace_fingerprint(r) != original
    artifact = Row(
        source_snapshot_json={"workspace_fingerprint": workspace_fingerprint(r)},
        content_json={"title": "合成工作稿"},
        checksum_sha256=content_checksum({"title": "合成工作稿"}),
    )
    assert artifact_source_state(artifact, r)["current"]
    r["requirements"][0].status = "ready"
    assert not artifact_source_state(artifact, r)["current"]


def test_legacy_snapshot_and_modified_content_never_reuse_approval():
    r = records()
    artifact = Row(
        source_snapshot_json={}, content_json={"title": "工作稿"}, checksum_sha256="incorrect"
    )
    state = artifact_source_state(artifact, r)
    assert not state["current"]
    assert len(state["reasons"]) == 2


def test_matrix_links_only_evidence_for_that_rule():
    r = records()
    rule_id = str(r["evidence"][0].eligibility_rule_id)
    r["eligibility"].criteria_json = [
        {"rule_id": rule_id, "name": "合成条件", "status": "PASS"},
        {"rule_id": str(uuid4()), "name": "缺失条件", "status": "MISSING"},
    ]
    rows = evidence_matrix(r)["rows"]
    assert len(rows[0]["policy_evidence"]) == 1
    assert rows[1]["policy_evidence"] == []
    assert "企业自述" in rows[0]["fact_source"]


@pytest.mark.parametrize(
    "key,field,before,after",
    [
        ("application", "title", "原项目名", "变更项目名"),
        ("profile", "snapshot_json", {"industry": "人工智能"}, {"industry": "其他"}),
        ("policy", "status", "published", "withdrawn"),
        ("documents", "checksum_sha256", "original", "changed"),
        ("rules", "expected_json", {"value": 1}, {"value": 2}),
        ("evidence", "article", "第一条", "第二条"),
    ],
)
def test_material_source_changes_invalidate_input_fingerprint(key, field, before, after):
    r = records()
    row = Row(id=uuid4(), **{field: before})
    r[key] = [row] if key in {"documents", "rules", "evidence"} else row
    fingerprint = workspace_fingerprint(r)
    setattr(row, field, after)
    assert workspace_fingerprint(r) != fingerprint


def test_changed_rule_cannot_be_legitimized_by_regenerating_a_fingerprint():
    rule = Row(
        id=uuid4(),
        status="active",
        fact_key="industry",
        operator="eq",
        expected_json={"value": "人工智能"},
        is_hard_gate=True,
        source_quote="支持人工智能",
    )
    version = Row(id=uuid4(), content="支持人工智能")
    profile = Row(snapshot_json={"industry": "人工智能"})
    result = Row(
        criteria_json=[
            {
                "rule_id": str(rule.id),
                "fact_key": "industry",
                "operator": "eq",
                "expected": "人工智能",
                "actual": "人工智能",
                "is_hard_gate": True,
                "status": "PASS",
            }
        ]
    )
    evidence = [
        Row(
            verified=True,
            eligibility_rule_id=rule.id,
            policy_version_id=version.id,
            quote=version.content,
            quote_start=0,
            quote_end=len(version.content),
        )
    ]
    assert not qualification_source_issues(result, [rule], profile, version, evidence)
    rule.expected_json = {"value": "生物医药"}
    assert qualification_source_issues(result, [rule], profile, version, evidence)
    rule.expected_json = {"value": "人工智能"}
    evidence[0].quote = "不支持人工智能"
    assert qualification_source_issues(result, [rule], profile, version, evidence)
