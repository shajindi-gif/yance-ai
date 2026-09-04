"""政策匹配引擎：Rule Engine + Semantic Retrieval + Rule Bonus + 可解释评分

匹配分必须可解释（section 19 of master task）。评分标准：
- 地区匹配: 20分 (省/市/区层级加权)
- 行业匹配: 15分 (精确匹配 15, 关键词 10, 无匹配 0)
- 企业规模: 10分 (按政策要求判断)
- 企业资质: 20分 (已获资质加分)
- 技术方向: 15分 (关键词匹配)
- 财务相关: 10分 (营收/研发费用)
- 语义相似度: 10分 (向量相似度 × 10)
总分: 100分
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Company, CompanyProfileVersion, Opportunity, Policy
from app.services.llm.registry import embed_texts
from app.services.policies.ingestion import latest_policy_version
from app.services.policies.retrieval import hybrid_policy_candidates
from app.services.policies.visibility import visible_policy_clause

# 行业关键词映射
INDUSTRY_KEYWORDS = {
    "人工智能": ["AI", "人工智能", "算力", "模型", "智能", "机器学习", "深度学习", "大模型", "GPU"],
    "软件": ["软件", "信息技术", "数字化", "信息化", "SaaS", "云服务", "数字经济"],
    "制造": ["制造", "工业", "装备", "机械", "智能制造", "自动化"],
    "生物医药": ["生物医药", "医疗器械", "创新药", "制药", "生物技术", "基因"],
    "新材料": ["新材料", "材料", "复合材料", "纳米", "高性能"],
    "集成电路": ["芯片", "半导体", "集成电路", "IC设计", "晶圆"],
    "新能源": ["新能源", "光伏", "储能", "锂电池", "氢能", "风电"],
    "航空航天": ["航空航天", "卫星", "低空经济", "无人机", "eVTOL"],
}


async def match_policies_for_company(
    db: Session,
    company: Company,
    tenant_id: UUID,
    *,
    scan_id: UUID | None = None,
    profile_version_id: UUID | None = None,
) -> list[Opportunity]:
    """
    为企业匹配全局政策库。
    使用 Rule Engine + Semantic Retrieval 混合评分。
    """
    # 1. 构建企业画像向量
    profile_version = None
    if profile_version_id:
        profile_version = db.scalar(
            select(CompanyProfileVersion).where(
                CompanyProfileVersion.id == profile_version_id,
                CompanyProfileVersion.company_id == company.id,
                CompanyProfileVersion.tenant_id == tenant_id,
            )
        )
        if not profile_version:
            raise ValueError("Company profile version is outside the scan scope")
    meta = profile_version.snapshot_json if profile_version else (company.metadata_json or {})
    def _string_list(value) -> list[str]:
        return [str(item) for item in value] if isinstance(value, list) else []

    profile_text = " ".join(
        str(value)
        for value in (
            company.name,
            meta.get("industry") or company.industry or "",
            meta.get("province") or company.province or "",
            meta.get("city") or company.city or "",
            " ".join(_string_list(meta.get("core_products"))),
            meta.get("rd_summary") or "",
        )
        if value
    )
    embeddings = await embed_texts([profile_text])
    company_vector = embeddings[0]

    # 2. 优先使用段落级词法 + 向量 RRF；为未迁移的旧记录保留整篇向量回退。
    candidates = hybrid_policy_candidates(
        db,
        tenant_id=tenant_id,
        query=profile_text,
        query_vector=company_vector,
        limit=50,
    )
    retrieval_chunks = {item.policy.id: item.chunk_ids for item in candidates}
    results = [(item.policy, item.similarity) for item in candidates]
    retrieval_mode = "hybrid_chunk_rrf"
    if not results:
        retrieval_mode = "legacy_document_vector"
        results = db.execute(
            select(
                Policy,
                (1 - Policy.embedding.cosine_distance(company_vector)).label("similarity"),
            )
            .where(
                visible_policy_clause(tenant_id),
                Policy.embedding.isnot(None),
                Policy.status == "published",
            )
            .order_by(Policy.embedding.cosine_distance(company_vector))
            .limit(50)
        ).all()

    if not results:
        return []

    # 3. 企业画像提取（从 metadata_json）
    company_scale = meta.get("company_scale") or meta.get("scale", "")
    raw_qualifications = meta.get("qualifications", [])
    company_qualifications = (
        list(raw_qualifications) if isinstance(raw_qualifications, list) else []
    )
    if meta.get("high_tech_status") == "已认定":
        company_qualifications.append("高新技术企业")
    if meta.get("tech_sme_status") == "已认定":
        company_qualifications.append("科技型中小企业")
    if meta.get("specialized_sme_status") == "已认定":
        company_qualifications.append("专精特新")
    try:
        company_rd_expense = float(meta.get("rd_expense_ratio", 0) or 0)
    except (ValueError, TypeError):
        company_rd_expense = 0.0
    try:
        company_revenue = float(meta.get("annual_revenue", 0) or 0)
    except (ValueError, TypeError):
        company_revenue = 0.0
    company_tech_keywords = " ".join(
        [
            str(meta.get("industry") or company.industry or "").lower(),
            " ".join(_string_list(meta.get("tech_stack"))),
            " ".join(_string_list(meta.get("core_products"))),
            str(meta.get("rd_summary") or ""),
        ]
    )

    # 4. 逐条政策评分
    opportunities = []
    for policy, semantic_sim in results:
        source_version = latest_policy_version(db, policy.id)
        score_breakdown = {}

        # ── 地区匹配 (20分) ──
        region_score = 0
        if company.province and policy.province:
            if company.province == policy.province:
                region_score = 15
                if company.city and policy.city and company.city == policy.city:
                    region_score = 18
                if company.city and policy.district and company.city == policy.district:
                    region_score = 20
            elif policy.level == "national":
                region_score = 20  # 国家政策全国适用
        elif policy.level == "national":
            region_score = 20
        elif not policy.province and not policy.level:
            region_score = 10  # 无地区限制
        score_breakdown["region"] = region_score

        # ── 行业匹配 (15分) ──
        industry_score = 0
        if company.industry:
            if policy.industry and company.industry == policy.industry:
                industry_score = 15
            else:
                # 关键词匹配
                for key, words in INDUSTRY_KEYWORDS.items():
                    if key in (company.industry or ""):
                        if any(w.lower() in (policy.content or "").lower() for w in words):
                            industry_score = max(industry_score, 10)
                        if any(w.lower() in (policy.industry or "").lower() for w in words):
                            industry_score = max(industry_score, 12)
        score_breakdown["industry"] = industry_score

        # ── 企业规模 (10分) ──
        scale_score = 5  # 默认（政策无规模要求）
        if company_scale and policy.policy_type:
            if "中小" in (policy.content or "") and company_scale in ["小型", "微型"]:
                scale_score = 10
            elif "大型" in (policy.content or "") and company_scale == "大型":
                scale_score = 10
            elif not any(kw in (policy.content or "") for kw in ["小型", "微型", "大型", "中小"]):
                scale_score = 8  # 政策未限定规模
        score_breakdown["scale"] = scale_score

        # ── 企业资质 (20分) ──
        qual_score = 0
        content_lower = (policy.content or "").lower()
        if "高新技术" in content_lower or "高企" in content_lower:
            if "高企" in company_qualifications or "高新技术企业" in company_qualifications:
                qual_score += 20
            else:
                qual_score += 5  # 尚未获得，可申报
        if "专精特新" in content_lower:
            if any("专精特新" in q for q in company_qualifications):
                qual_score += 15
            else:
                qual_score += 5
        if "科技型中小企业" in content_lower:
            if "科技型中小企业" in company_qualifications:
                qual_score += 15
            else:
                qual_score += 5
        qual_score = min(qual_score, 20)
        score_breakdown["qualification"] = qual_score

        # ── 技术方向 (15分) ──
        tech_score = 0
        for key, words in INDUSTRY_KEYWORDS.items():
            if key in company_tech_keywords:
                matches = sum(1 for w in words if w.lower() in content_lower)
                if matches >= 2:
                    tech_score = max(tech_score, 15)
                elif matches >= 1:
                    tech_score = max(tech_score, 10)
        if tech_score == 0:
            tech_score = 5  # 默认
        score_breakdown["tech"] = tech_score

        # ── 财务相关 (10分) ──
        finance_score = 5  # 默认
        if "研发费用" in content_lower or "研发支出" in content_lower:
            if company_rd_expense and company_rd_expense > 3:
                finance_score = 10
            elif company_rd_expense:
                finance_score = 7
        if "营业收入" in content_lower and company_revenue:
            finance_score = min(finance_score + 3, 10)
        score_breakdown["finance"] = finance_score

        # ── 语义相似度 (10分) ──
        semantic_score = round(semantic_sim * 10, 1)
        score_breakdown["semantic"] = semantic_score

        # ── 总分 ──
        final_score = sum(score_breakdown.values())
        final_score = max(0, min(100, final_score))
        # ── 生成 evidence ──
        evidence = {
            "score_breakdown": score_breakdown,
            "total_score": final_score,
            "jurisdiction_match": region_score >= 15,
            "industry_match": industry_score >= 10,
            "support_amount": policy.support_amount or "未公开",
            "support_type": policy.support_type or "",
            "deadline": policy.deadline.isoformat() if policy.deadline else None,
            "level": policy.level or "",
            "gap_analysis_status": "not_verified_against_documents",
            "retrieval": {
                "mode": retrieval_mode,
                "policy_version_id": str(source_version.id) if source_version else None,
                "chunk_ids": [str(item) for item in retrieval_chunks.get(policy.id, ())],
            },
        }

        # ── 判断缺失材料 ──
        missing = []
        if "知识产权" in content_lower or "专利" in content_lower:
            missing.append("知识产权证明（专利/软著）")
        if "研发费用" in content_lower:
            missing.append("研发费用专项审计报告")
        if "营业收入" in content_lower or "销售收入" in content_lower:
            missing.append("近三年财务审计报告")
        if "研发人员" in content_lower or "科技人员" in content_lower:
            missing.append("研发人员名单及社保缴纳证明")
        if "高新技术" in content_lower and "高企" not in company_qualifications:
            missing.append("高新技术企业认定申请")
        if not missing:
            missing.append("基本申报材料（营业执照、企业简介）")
        evidence["missing_materials"] = missing

        policy_snapshot = {
            "title": policy.title,
            "issuing_authority": policy.issuing_authority,
            "jurisdiction": policy.jurisdiction,
            "level": policy.level,
            "province": policy.province,
            "city": policy.city,
            "district": policy.district,
            "industry": policy.industry,
            "policy_type": policy.policy_type,
            "source_url": policy.source_url,
            "published_at": policy.published_at.isoformat() if policy.published_at else None,
            "effective_at": policy.effective_at.isoformat() if policy.effective_at else None,
            "deadline": policy.deadline.isoformat() if policy.deadline else None,
            "support_amount": policy.support_amount,
            "support_type": policy.support_type,
            "policy_version_id": str(source_version.id) if source_version else None,
        }
        opp = None
        if scan_id:
            opp = db.scalar(
                select(Opportunity).where(
                    Opportunity.tenant_id == tenant_id,
                    Opportunity.scan_id == scan_id,
                    Opportunity.policy_id == policy.id,
                )
            )
        else:
            opp = db.scalar(
                select(Opportunity)
                .where(
                    Opportunity.tenant_id == tenant_id,
                    Opportunity.company_id == company.id,
                    Opportunity.policy_id == policy.id,
                    Opportunity.scan_id.is_(None),
                )
                .order_by(Opportunity.created_at.desc())
            )
        if opp:
            opp.score = final_score / 100.0
            opp.evidence_json = evidence
            opp.policy_snapshot_json = policy_snapshot
            opp.policy_version_id = source_version.id if source_version else None
        else:
            opp = Opportunity(
                tenant_id=tenant_id,
                company_id=company.id,
                policy_id=policy.id,
                policy_version_id=source_version.id if source_version else None,
                scan_id=scan_id,
                profile_version_id=profile_version_id,
                title=f"{company.name} × {policy.title}",
                score=final_score / 100.0,
                status="identified",
                evidence_json=evidence,
                policy_snapshot_json=policy_snapshot,
                eligibility_status="NEED_MORE_INFORMATION",
            )
        opportunities.append(opp)

    # 5. 按总分排序，存入数据库
    opportunities.sort(key=lambda o: o.score, reverse=True)
    for opp in opportunities:
        db.add(opp)
    db.commit()
    return opportunities
