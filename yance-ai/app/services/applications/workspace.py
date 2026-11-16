from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import (
    Application,
    ApplicationArtifact,
    ApplicationDocumentLink,
    ApplicationRequirement,
    Company,
    CompanyProfileVersion,
    Document,
    EligibilityResult,
    EligibilityRule,
    Evidence,
    Opportunity,
    Policy,
    PolicyVersion,
)
from app.services.applications.artifacts import content_checksum
from app.services.policies.applicability import policy_context_issues
from app.services.policies.visibility import visible_policy_clause


def workspace_records(db: Session, application: Application) -> dict[str, Any]:
    company = db.scalar(
        select(Company).where(
            Company.id == application.company_id, Company.tenant_id == application.tenant_id
        )
    )
    opportunity = (
        db.scalar(
            select(Opportunity).where(
                Opportunity.id == application.opportunity_id,
                Opportunity.tenant_id == application.tenant_id,
            )
        )
        if application.opportunity_id
        else None
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
    profile = db.scalar(
        select(CompanyProfileVersion)
        .where(
            CompanyProfileVersion.company_id == application.company_id,
            CompanyProfileVersion.tenant_id == application.tenant_id,
        )
        .order_by(CompanyProfileVersion.version.desc())
    )
    policy = (
        db.scalar(
            select(Policy).where(
                Policy.id == opportunity.policy_id,
                visible_policy_clause(application.tenant_id),
            )
        )
        if opportunity
        else None
    )
    version = (
        db.scalar(
            select(PolicyVersion).where(
                PolicyVersion.id == opportunity.policy_version_id,
                PolicyVersion.policy_id == policy.id,
                PolicyVersion.tenant_id.in_([application.tenant_id])
                | PolicyVersion.tenant_id.is_(None),
            )
        )
        if policy
        else None
    )
    latest_version = (
        db.scalar(
            select(PolicyVersion.id)
            .where(
                PolicyVersion.policy_id == policy.id,
                PolicyVersion.tenant_id.in_([application.tenant_id])
                | PolicyVersion.tenant_id.is_(None),
            )
            .order_by(PolicyVersion.version.desc())
        )
        if policy
        else None
    )
    documents = (
        list(
            db.scalars(
                select(Document)
                .where(
                    Document.id.in_([link.document_id for link in links]),
                    Document.tenant_id == application.tenant_id,
                )
                .order_by(Document.id)
            ).all()
        )
        if links
        else []
    )
    rules = (
        list(
            db.scalars(
                select(EligibilityRule)
                .where(
                    EligibilityRule.policy_version_id == version.id,
                    EligibilityRule.tenant_id.in_([application.tenant_id])
                    | EligibilityRule.tenant_id.is_(None),
                )
                .order_by(EligibilityRule.id)
            ).all()
        )
        if version
        else []
    )
    context_issues = policy_context_issues(
        policy, version, profile.snapshot_json if profile else {}
    )
    if opportunity and (not profile or profile.id != opportunity.profile_version_id):
        context_issues.append("企业已发布资料版本变化或缺失，请重新扫描资格")
    if version and version.id != latest_version:
        context_issues.append("政策已有新版本，请重新扫描并复核")
    context_issues.extend(
        qualification_source_issues(eligibility, rules, profile, version, evidence)
    )
    return {
        "application": application,
        "profile": profile,
        "policy": policy,
        "policy_version": version,
        "documents": documents,
        "rules": rules,
        "context_issues": context_issues,
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
    blockers = list(hard_blockers) + records.get("context_issues", [])
    if not eligibility:
        blockers.append("缺少资格判断")
    elif eligibility.status not in {"ELIGIBLE", "POTENTIALLY_ELIGIBLE"}:
        blockers.append(f"资格状态为 {eligibility.status}")
    if eligibility and any(
        row.get("is_hard_gate") and row.get("status") != "PASS"
        for row in (eligibility.criteria_json or [])
    ):
        blockers.append("仍有未满足或未核验的资格硬条件")
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
        "disclaimer": "本文件为证据型工作稿，企业资料由客户提供；正式使用或提交前须由客户本人或其授权团队成员核对原文、企业事实和材料。客户确认不代表政府认定或获批，衍策不提供人工业务审核。",
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
        "workspace_fingerprint": workspace_fingerprint(records),
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


def _values(row, fields: str) -> dict[str, Any] | None:
    if row is None:
        return None
    import json

    return json.loads(
        json.dumps({key: getattr(row, key, None) for key in fields.split()}, default=str)
    )


def workspace_fingerprint(records: dict[str, Any]) -> str:
    """Versioned semantic inputs, excluding volatile timestamps and review state."""
    payload = {
        "contract": "workspace-inputs-v1",
        "application": _values(
            records.get("application"), "id company_id opportunity_id title due_at form_data"
        ),
        "company": _values(records.get("company"), "id name"),
        "profile": _values(records.get("profile"), "id snapshot_json"),
        "policy": _values(
            records.get("policy"), "id status effective_at expires_at deadline content"
        ),
        "policy_version": _values(
            records.get("policy_version"),
            "id status content_sha256 content effective_date expiry_date application_deadline",
        ),
        "eligibility": _values(
            records.get("eligibility"),
            "id status criteria_json missing_information_json profile_version_id policy_version_id",
        ),
    }
    for key, fields in {
        "requirements": "id title description status is_hard_gate source_json",
        "evidence": "id eligibility_rule_id quote verified policy_version_id policy_chunk_id quote_start quote_end source_title source_url issuer article",
        "links": "id document_id requirement_id status",
        "documents": "id status ingestion_status checksum_sha256 size_bytes",
        "rules": "id status fact_key operator expected_json is_hard_gate source_quote",
    }.items():
        payload[key] = [
            _values(row, fields)
            for row in sorted(records.get(key, []), key=lambda item: str(item.id))
        ]
    return content_checksum(payload)


def artifact_source_state(artifact: ApplicationArtifact, records: dict[str, Any]) -> dict[str, Any]:
    fingerprint = (artifact.source_snapshot_json or {}).get("workspace_fingerprint")
    reasons = list(records.get("context_issues", []))
    if not fingerprint:
        reasons.append("历史工作稿缺少输入指纹，请重新生成后复核")
    elif fingerprint != workspace_fingerprint(records):
        reasons.append("企业资料、政策规则、材料或证据已变化，请重新生成并复核")
    if artifact.checksum_sha256 != content_checksum(artifact.content_json):
        reasons.append("工作稿内容校验失败")
    return {"current": not reasons, "reasons": list(dict.fromkeys(reasons))}


def evidence_matrix(records: dict[str, Any]) -> dict[str, Any]:
    result = records.get("eligibility")
    rows = []
    for criterion in (result.criteria_json or []) if result else []:
        rule_id = criterion.get("rule_id")
        sources = [
            item
            for item in records["evidence"]
            if rule_id and str(item.eligibility_rule_id) == rule_id
        ]
        rows.append(
            {
                **criterion,
                "policy_evidence": [
                    {
                        "id": str(item.id),
                        "quote": item.quote,
                        "article": item.article,
                        "source_url": item.source_url,
                        "verified": item.verified,
                    }
                    for item in sources
                ],
                "profile_version_id": str(result.profile_version_id)
                if result.profile_version_id
                else None,
                "fact_source": "已发布企业画像；企业自述，不代表第三方鉴证",
            }
        )
    return {
        "rows": rows,
        "status": result.status if result else "NEED_MORE_INFORMATION",
        "context_issues": records.get("context_issues", []),
        "missing_information": result.missing_information_json if result else ["缺少资格判断"],
    }


def qualification_source_issues(eligibility, rules, profile, version, evidence) -> list[str]:
    """Check the stored decision contract without making a new eligibility decision."""
    if not eligibility:
        return []
    active = {str(rule.id): rule for rule in rules if rule.status == "active"}
    criteria = {row.get("rule_id"): row for row in (eligibility.criteria_json or [])}
    issues = []
    if not any(rule.is_hard_gate for rule in active.values()):
        issues.append("缺少已审核的资格硬条件，请重新核验")
    if set(criteria) != set(active):
        issues.append("资格规则集合已变化，请重新扫描")
    snapshot = profile.snapshot_json if profile else {}
    for rule_id, rule in active.items():
        row = criteria.get(rule_id, {})
        expected = (
            rule.expected_json.get("value")
            if "value" in rule.expected_json
            else rule.expected_json.get("values")
        )
        if (
            row.get("fact_key") != rule.fact_key
            or row.get("operator") != rule.operator
            or row.get("expected") != expected
            or row.get("actual") != snapshot.get(rule.fact_key)
            or row.get("is_hard_gate") != rule.is_hard_gate
        ):
            issues.append("资格规则或企业事实与原判断不一致，请重新扫描")
        if rule.is_hard_gate and row.get("status") == "PASS":
            supported = any(
                item.verified
                and str(item.eligibility_rule_id) == rule_id
                and version
                and item.policy_version_id == version.id
                and item.quote == rule.source_quote
                and version.content[item.quote_start : item.quote_end] == item.quote
                for item in evidence
            )
            if not supported:
                issues.append("资格硬条件缺少当前版本的逐条原文证据")
    return list(dict.fromkeys(issues))
