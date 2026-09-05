from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Company, CompanyFact, CompanyProfile, CompanyProfileVersion
from app.schemas.schemas import CompanyProfileData

COMPLETENESS_FIELDS = (
    "industry",
    "province",
    "registered_address",
    "founded_date",
    "company_scale",
    "revenue_stage",
    "funding_stage",
    "high_tech_status",
    "tech_sme_status",
    "specialized_sme_status",
    "intellectual_property",
    "core_products",
    "rd_summary",
    "talent_summary",
    "projects",
    "current_needs",
)


def profile_completeness(data: dict[str, Any]) -> int:
    populated = sum(
        1
        for field in COMPLETENESS_FIELDS
        if data.get(field) is not None and data.get(field) != "" and data.get(field) != []
    )
    return round(populated / len(COMPLETENESS_FIELDS) * 100)


def initial_profile_data(company: Company) -> dict[str, Any]:
    legacy = company.metadata_json or {}
    qualifications = legacy.get("qualifications", [])
    if not isinstance(qualifications, list):
        qualifications = []

    def _list_value(key: str) -> list[str]:
        value = legacy.get(key, [])
        return [str(item) for item in value] if isinstance(value, list) else []

    candidate = {
        "industry": company.industry,
        "province": company.province,
        "city": company.city,
        "registered_address": legacy.get("registered_address"),
        "founded_date": legacy.get("founded_date"),
        "company_scale": legacy.get("company_scale") or legacy.get("scale"),
        "employee_count": legacy.get("employee_count"),
        "revenue_stage": legacy.get("revenue_stage"),
        "annual_revenue": legacy.get("annual_revenue"),
        "funding_stage": legacy.get("funding_stage"),
        "high_tech_status": legacy.get("high_tech_status")
        or ("已认定" if any(item in ("高企", "高新技术企业") for item in qualifications) else None),
        "tech_sme_status": legacy.get("tech_sme_status")
        or ("已认定" if "科技型中小企业" in qualifications else None),
        "specialized_sme_status": legacy.get("specialized_sme_status")
        or ("已认定" if any("专精特新" in item for item in qualifications) else None),
        "intellectual_property": _list_value("intellectual_property"),
        "core_products": _list_value("core_products"),
        "rd_summary": legacy.get("rd_summary"),
        "rd_expense_ratio": legacy.get("rd_expense_ratio"),
        "talent_summary": legacy.get("talent_summary"),
        "projects": _list_value("projects"),
        "current_needs": _list_value("current_needs") or _list_value("policy_needs"),
    }
    try:
        data = CompanyProfileData.model_validate(candidate).model_dump(mode="json")
    except ValueError:
        data = CompanyProfileData(
            industry=company.industry,
            province=company.province,
            city=company.city,
        ).model_dump(mode="json")
    return data


def create_company_profile(db: Session, company: Company) -> CompanyProfile:
    data = initial_profile_data(company)
    profile = CompanyProfile(
        tenant_id=company.tenant_id,
        company_id=company.id,
        status="draft",
        draft_json=data,
        completeness_score=profile_completeness(data),
    )
    db.add(profile)
    db.flush()
    return profile


def get_or_create_company_profile(db: Session, company: Company) -> CompanyProfile:
    profile = db.scalar(
        select(CompanyProfile).where(
            CompanyProfile.company_id == company.id,
            CompanyProfile.tenant_id == company.tenant_id,
        )
    )
    return profile or create_company_profile(db, company)


def publish_company_profile(
    db: Session, profile: CompanyProfile, *, created_by
) -> CompanyProfileVersion:
    version_number = (profile.published_version or 0) + 1
    snapshot = CompanyProfileData.model_validate(profile.draft_json).model_dump(mode="json")
    completeness = profile_completeness(snapshot)
    version = CompanyProfileVersion(
        tenant_id=profile.tenant_id,
        profile_id=profile.id,
        company_id=profile.company_id,
        version=version_number,
        snapshot_json=snapshot,
        completeness_score=completeness,
        created_by=created_by,
    )
    db.add(version)
    db.flush()
    for key, value in snapshot.items():
        if value is None or value == "" or value == []:
            continue
        db.add(
            CompanyFact(
                tenant_id=profile.tenant_id,
                profile_version_id=version.id,
                fact_key=key,
                value_json={"value": value},
                confidence=1,
                extraction_method="user_asserted",
                verification_status="user_asserted",
            )
        )
    profile.status = "published"
    profile.completeness_score = completeness
    profile.published_version = version_number
    profile.published_at = version.published_at
    return version
