"""Unit tests for deterministic POLICY_REPORT usefulness ranking."""

from datetime import UTC, datetime, timedelta

from app.services.report.ranking import (
    compute_rank_features,
    enforce_local_diversity,
    is_activity_or_plan_title,
    region_fit_score,
)


def test_local_outranks_national_for_shanghai_profile():
    local = compute_rank_features(
        title="上海市关于组织申报专精特新中小企业的通知",
        policy_type="通知",
        company_province="上海市",
        company_city="上海市",
        company_district=None,
        policy_province="上海市",
        policy_city="上海市",
        policy_district=None,
        policy_level="provincial",
        industry_component=12,
        scale_component=8,
        qualification_component=15,
        tech_component=10,
        finance_component=5,
        semantic_component=6,
        active_hard_rules=2,
        deadline=datetime.now(UTC) + timedelta(days=20),
        expires_at=None,
    )
    national_promo = compute_rank_features(
        title="两部门关于开展2026年全国中小企业法律政策宣传月活动的通知",
        policy_type="通知",
        company_province="上海市",
        company_city="上海市",
        company_district=None,
        policy_province=None,
        policy_city=None,
        policy_district=None,
        policy_level="national",
        industry_component=10,
        scale_component=8,
        qualification_component=5,
        tech_component=10,
        finance_component=5,
        semantic_component=8,
        active_hard_rules=0,
        deadline=None,
        expires_at=None,
    )
    assert local.skip is False
    assert national_promo.skip is True or local.final_score > national_promo.final_score
    assert local.region_fit > national_promo.region_fit or national_promo.skip


def test_activity_without_rules_skipped():
    ranked = compute_rank_features(
        title="关于印发《会计改革与发展“十五五”规划》的通知",
        policy_type="规划",
        company_province="上海市",
        company_city=None,
        company_district=None,
        policy_province=None,
        policy_city=None,
        policy_district=None,
        policy_level="national",
        industry_component=5,
        scale_component=5,
        qualification_component=5,
        tech_component=5,
        finance_component=5,
        semantic_component=9,
        active_hard_rules=0,
        deadline=None,
        expires_at=None,
    )
    assert ranked.skip is True
    assert ranked.skip_reason == "activity_or_plan_noise"


def test_recruitment_skipped_even_with_rules():
    ranked = compute_rank_features(
        title="国家知识产权局知识产权发展研究中心2026年第二批项目博士后招聘公告",
        policy_type="公告",
        company_province="上海市",
        company_city=None,
        company_district=None,
        policy_province=None,
        policy_city=None,
        policy_district=None,
        policy_level="national",
        industry_component=12,
        scale_component=5,
        qualification_component=15,
        tech_component=10,
        finance_component=5,
        semantic_component=8,
        active_hard_rules=2,
        deadline=None,
        expires_at=None,
    )
    assert ranked.skip is True


def test_out_of_region_hard_skip():
    score, out = region_fit_score(
        company_province="上海市",
        company_city=None,
        company_district=None,
        policy_province="广东省",
        policy_city=None,
        policy_district=None,
        policy_level="provincial",
    )
    assert out is True
    assert score == 0


def test_activity_token_detection():
    assert is_activity_or_plan_title("开展宣传月活动的通知")
    assert is_activity_or_plan_title("百场万企大中小企业融通对接活动")


def test_local_diversity_injects_province_into_top():
    items = [
        {"id": "n1", "province": None},
        {"id": "n2", "province": None},
        {"id": "n3", "province": None},
        {"id": "n4", "province": None},
        {"id": "s1", "province": "上海市"},
        {"id": "s2", "province": "上海市"},
        {"id": "s3", "province": "上海市"},
    ]
    ordered = enforce_local_diversity(
        items,
        company_province="上海市",
        top_n=4,
        min_local=3,
        province_getter=lambda x: x["province"],
    )
    top_provinces = [x["province"] for x in ordered[:4]]
    assert top_provinces.count("上海市") >= 3
