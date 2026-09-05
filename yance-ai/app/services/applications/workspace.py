from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import (
    Application,
    ApplicationArtifact,
    ApplicationDocumentLink,
    ApplicationRequirement,
    Company,
    EligibilityResult,
    Evidence,
    Opportunity,
)
from app.services.applications.artifacts import content_checksum


def workspace_records(db: Session, application: Application) -> dict[str, Any]:
    company = db.get(Company, application.company_id)
    opportunity = (
        db.get(Opportunity, application.opportunity_id) if application.opportunity_id else None
    )
    eligibility = (
        db.scalar(
            select(EligibilityResult).where(
                EligibilityResult.opportunity_id == opportunity.id,
                EligibilityResult.tenant_id == application.tenant_id,
            )
        )
        if opportunity
        else None
    )
    requirements = list(
        db.scalars(
            select(ApplicationRequirement)
            .where(
                ApplicationRequirement.application_id == application.id,
                ApplicationRequirement.tenant_id == application.tenant_id,
            )
            .order_by(ApplicationRequirement.sort_order)
        ).all()
    )
    evidence = (
        list(
            db.scalars(
                select(Evidence)
                .where(
                    Evidence.eligibility_result_id == eligibility.id,
                    Evidence.tenant_id == application.tenant_id,
                )
                .order_by(Evidence.created_at)
            ).all()
        )
        if eligibility
        else []
    )
    links = list(
        db.scalars(
            select(ApplicationDocumentLink)
            .where(
                ApplicationDocumentLink.application_id == application.id,
                ApplicationDocumentLink.tenant_id == application.tenant_id,
            )
            .order_by(ApplicationDocumentLink.created_at)
        ).all()
    )
    return {
        "company": company,
        "opportunity": opportunity,
        "eligibility": eligibility,
        "requirements": requirements,
        "evidence": evidence,
        "links": links,
    }


def readiness(records: dict[str, Any]) -> dict[str, Any]:
    requirements = records["requirements"]
    hard_blockers = [
        item.title
        for item in requirements
        if item.is_hard_gate and item.status not in {"ready", "approved", "not_applicable"}
    ]
    missing = [item.title for item in requirements if item.status in {"missing", "collecting"}]
    eligibility = records["eligibility"]
    evidence_count = sum(bool(item.verified) for item in records["evidence"])
    blockers = list(hard_blockers)
    if not eligibility:
        blockers.append("缺少资格判断")
    elif eligibility.status in {"NOT_ELIGIBLE", "NEED_MORE_INFORMATION"}:
        blockers.append(f"资格状态为 {eligibility.status}")
    if (
        eligibility
        and eligibility.status in {"ELIGIBLE", "POTENTIALLY_ELIGIBLE"}
        and evidence_count == 0
    ):
        blockers.append("缺少已核验政策证据")
    return {
        "requirement_total": len(requirements),
        "requirement_ready": sum(
            item.status in {"ready", "approved", "not_applicable"} for item in requirements
        ),
        "hard_gate_blockers": hard_blockers,
        "missing_requirements": missing,
        "linked_documents": len(records["links"]),
        "verified_evidence": evidence_count,
        "blockers": list(dict.fromkeys(blockers)),
        "can_submit_for_review": not blockers,
    }


def build_content(
    application: Application,
    records: dict[str, Any],
    *,
    revision_note: str | None = None,
    executive_summary: str | None = None,
    title: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    company = records["company"]
    opportunity = records["opportunity"]
    eligibility = records["eligibility"]
    status = eligibility.status if eligibility else "NEED_MORE_INFORMATION"
    summary = executive_summary or (
        eligibility.summary if eligibility else "尚无结构化资格判断，不能形成确定性申报结论。"
    )
    content = {
        "schema_version": "application-brief-v1",
        "title": title or f"{application.title} — 申报工作稿",
        "company_name": company.name if company else "",
        "disclaimer": "本文件为证据型工作稿，正式提交前必须由授权人员复核。",
        "executive_summary": summary,
        "eligibility": {
            "status": status,
            "summary": eligibility.summary if eligibility else summary,
        },
        "criteria": list(eligibility.criteria_json if eligibility else []),
        "requirements": [
            {
                "id": str(item.id),
                "title": item.title,
                "description": item.description,
                "status": item.status,
                "is_hard_gate": item.is_hard_gate,
                "source": item.source_json,
            }
            for item in records["requirements"]
        ],
        "evidence": [
            {
                "id": str(item.id),
                "source_title": item.source_title,
                "source_url": item.source_url,
                "issuer": item.issuer,
                "article": item.article,
                "quote": item.quote,
                "verified": item.verified,
            }
            for item in records["evidence"]
        ],
        "revision_note": revision_note,
    }
    source_snapshot = {
        "application_id": str(application.id),
        "company_id": str(application.company_id),
        "opportunity_id": str(opportunity.id) if opportunity else None,
        "profile_version_id": str(opportunity.profile_version_id)
        if opportunity and opportunity.profile_version_id
        else None,
        "policy_version_id": str(opportunity.policy_version_id)
        if opportunity and opportunity.policy_version_id
        else None,
        "eligibility_result_id": str(eligibility.id) if eligibility else None,
        "requirement_ids": [str(item.id) for item in records["requirements"]],
        "document_link_ids": [str(item.id) for item in records["links"]],
        "evidence_ids": [str(item.id) for item in records["evidence"]],
    }
    return content, source_snapshot


def create_artifact(
    db: Session,
    application: Application,
    *,
    user_id,
    revision_note: str | None = None,
    executive_summary: str | None = None,
    title: str | None = None,
) -> ApplicationArtifact:
    db.execute(select(Application.id).where(Application.id == application.id).with_for_update())
    records = workspace_records(db, application)
    eligibility = records["eligibility"]
    if eligibility and eligibility.status == "NOT_ELIGIBLE":
        raise ValueError("已核验硬门槛不满足，不能生成申报工作稿")
    version = (
        db.scalar(
            select(func.max(ApplicationArtifact.version)).where(
                ApplicationArtifact.application_id == application.id,
                ApplicationArtifact.artifact_type == "application_brief",
            )
        )
        or 0
    ) + 1
    content, source_snapshot = build_content(
        application,
        records,
        revision_note=revision_note,
        executive_summary=executive_summary,
        title=title,
    )
    artifact = ApplicationArtifact(
        tenant_id=application.tenant_id,
        application_id=application.id,
        created_by=user_id,
        artifact_type="application_brief",
        title=content["title"],
        version=version,
        status="draft",
        generation_method="deterministic-evidence-v1",
        content_json=content,
        source_snapshot_json=source_snapshot,
        checksum_sha256=content_checksum(content),
    )
    db.add(artifact)
    db.flush()
    return artifact
