"""Park catalogue validation and jurisdiction logic.

These tests are the regression wall for the two failure modes the product cannot
afford: (a) a park count that overstates verification, (b) an enterprise being
granted a park policy because its postal address happens to sit in the park's city.
"""

from __future__ import annotations

import pytest

from app.services.park_registry import catalog as catalog_mod
from app.services.park_registry.geography import (
    AttachmentStatus,
    ScopeVerdict,
    address_is_not_entitlement,
    evaluate_scope,
    resolve_park_attachment,
)


@pytest.fixture(scope="module")
def catalog():
    return catalog_mod.load_catalog()


def test_catalog_loads_and_counts_first_batch(catalog):
    assert len(catalog.records) >= 30
    htz = [r for r in catalog.records if r.park_type == "national_high_tech_zone"]
    # 首批 30 个重点科创城市，每城一个代表性国家高新区。
    assert len(htz) == 30


def test_catalog_does_not_infer_district_or_boundary(catalog):
    """No park may claim a confirmed boundary without an explicit source."""
    for record in catalog.records:
        if record.boundary_status == "confirmed":
            assert record.source_url, f"{record.park_id} 声称已确认边界但缺少来源"
    # 本轮没有核验过任何园区边界，因此全部应为 needs_confirmation。
    assert all(r.boundary_status == "needs_confirmation" for r in catalog.records)


def test_registered_is_not_coverage(catalog):
    coverage = catalog.coverage()
    assert coverage["total_registered"] == len(catalog.records)
    # registered 不等于已核验：metadata_verified 才是覆盖口径。
    assert coverage["metadata_verified"] == 0
    assert coverage["usable_for_matching"] == 0
    assert "不等于已连通" in coverage["note"]


def test_zone_types_are_not_merged(catalog):
    """苏州高新区 与 苏州工业园区 是两个独立主体，不得合并计数。"""
    hits = [r for r in catalog.records if r.city == "苏州市"]
    assert len(hits) == 2
    types = {r.park_type for r in hits}
    assert types == {"national_high_tech_zone", "economic_dev_zone"}


def test_exact_name_lookup_refuses_fuzzy_park_assignment(catalog):
    assert catalog_mod.match_park_by_name(catalog, "苏州") == []
    exact = catalog_mod.match_park_by_name(catalog, "苏州工业园区")
    assert [r.park_id for r in exact] == ["park_sz_sip"]
    alias = catalog_mod.match_park_by_name(catalog, "中国光谷")
    assert [r.park_id for r in alias] == ["park_wh_dh"]


def test_address_only_snapshot_cannot_grant_park_membership(catalog):
    park = catalog.by_id()["park_wh_dh"]
    facts = {
        "address_province": "湖北省",
        "address_city": "武汉市",
        "address_district": "洪山区",
        "address_text": "武汉市洪山区光谷大道 1 号",
    }
    result = resolve_park_attachment(park, facts, required="registered_in_park")
    assert result.status is AttachmentStatus.NEEDS_CONFIRMATION
    assert "地址" in result.reason
    assert address_is_not_entitlement(facts) is True


def test_different_qualification_basis_is_not_interchangeable(catalog):
    park = catalog.by_id()["park_wh_dh"]
    # 企业在园区纳税，但政策要求的是注册关系 —— 不能视为满足。
    facts = {"tax_park_id": "park_wh_dh"}
    result = resolve_park_attachment(park, facts, required="registered_in_park")
    assert result.status is AttachmentStatus.NEEDS_CONFIRMATION
    assert "注册地" in result.reason


def test_enterprise_in_another_park_is_explicitly_not_member(catalog):
    park = catalog.by_id()["park_sz_jj"]
    facts = {"registered_park_id": "park_sz_sip"}
    result = resolve_park_attachment(park, facts, required="registered_in_park")
    assert result.status is AttachmentStatus.NOT_MEMBER
    assert "park_sz_sip" in result.reason


def test_unconfirmed_boundary_blocks_park_scope(catalog):
    park = catalog.by_id()["park_wh_dh"]
    scope = {
        "scope_type": "park",
        "park_id": "park_wh_dh",
        "qualification_basis": "registered_in_park",
        "requires_confirmation": False,
        "review_status": "confirmed",
    }
    result = evaluate_scope(scope, {"registered_park_id": "park_wh_dh"}, park=park)
    assert result.verdict is ScopeVerdict.NEEDS_REVIEW
    assert result.basis == "park_boundary"


def test_unspecified_park_basis_requires_human_review(catalog):
    park = catalog.by_id()["park_wh_dh"]
    _scope = {
        "scope_type": "park",
        "park_id": "park_wh_dh",
        "qualification_basis": "unspecified",
        "requires_confirmation": False,
        "review_status": "confirmed",
    }
    # 即使边界已知，也要先通过 boundary 检查；这里直接验证 attachment 层语义。
    attachment = resolve_park_attachment(park, {"registered_park_id": "park_wh_dh"}, required="unspecified")
    assert attachment.status is AttachmentStatus.NEEDS_CONFIRMATION
    assert "未明确要求" in attachment.reason


def test_provincial_scope_is_not_narrowed_to_capital():
    """省级政策：省内任何地市企业都应命中，不能被误缩为省会。"""
    scope = {
        "scope_type": "province",
        "province": "浙江省",
        "city": None,
        "district": None,
        "requires_confirmation": False,
        "review_status": "confirmed",
    }
    result = evaluate_scope(scope, {"province": "浙江省", "city": "宁波市"})
    assert result.verdict is ScopeVerdict.SATISFIED

    other = evaluate_scope(scope, {"province": "江苏省", "city": "苏州市"})
    assert other.verdict is ScopeVerdict.NOT_SATISFIED


def test_city_scope_mismatch_is_not_satisfied():
    scope = {
        "scope_type": "city",
        "province": "江苏省",
        "city": "苏州市",
        "requires_confirmation": False,
        "review_status": "confirmed",
    }
    assert evaluate_scope(scope, {"province": "江苏省", "city": "南京市"}).verdict is ScopeVerdict.NOT_SATISFIED
    assert evaluate_scope(scope, {"province": "江苏省"}).verdict is ScopeVerdict.INSUFFICIENT


def test_unreviewed_scope_needs_review_before_any_conclusion():
    scope = {
        "scope_type": "city",
        "province": "江苏省",
        "city": "苏州市",
        "requires_confirmation": True,
        "review_status": "draft",
    }
    assert evaluate_scope(scope, {"province": "江苏省", "city": "苏州市"}).verdict is ScopeVerdict.NEEDS_REVIEW


def test_catalog_rejects_alias_collision(tmp_path):
    """别名冲突会让匹配落到错误的园区，必须在加载期失败。"""
    base = {
        "catalog_version": "test",
        "parks": [
            {
                "park_id": "p1", "name": "甲园区", "aliases": ["同名"],
                "park_type": "tech_park", "province": "A省", "city": "A市",
                "status": "active", "boundary_status": "needs_confirmation",
                "verification_status": "registered",
            },
            {
                "park_id": "p2", "name": "乙园区", "aliases": ["同名"],
                "park_type": "tech_park", "province": "A省", "city": "A市",
                "status": "active", "boundary_status": "needs_confirmation",
                "verification_status": "registered",
            },
        ],
    }
    import yaml

    (tmp_path / "dup.yaml").write_text(yaml.safe_dump(base, allow_unicode=True), encoding="utf-8")
    with pytest.raises(catalog_mod.ParkCatalogError, match="别名冲突"):
        catalog_mod.load_catalog(tmp_path)


def test_catalog_rejects_confirmed_boundary_without_source(tmp_path):
    import yaml

    payload = {
        "catalog_version": "test",
        "parks": [{
            "park_id": "p1", "name": "甲园区", "park_type": "tech_park",
            "province": "A省", "city": "A市", "status": "active",
            "boundary_status": "confirmed", "verification_status": "metadata_verified",
            "source_url": None,
        }],
    }
    (tmp_path / "bad.yaml").write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    with pytest.raises(catalog_mod.ParkCatalogError, match="必须提供 source_url"):
        catalog_mod.load_catalog(tmp_path)
