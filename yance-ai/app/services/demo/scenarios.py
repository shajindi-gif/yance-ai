from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.models import (
    Agent,
    AgentRun,
    AgentStep,
    Application,
    ApplicationActivity,
    ApplicationArtifact,
    ApplicationDocumentLink,
    ApplicationRequirement,
    Company,
    CompanyFact,
    CompanyProfile,
    CompanyProfileVersion,
    DemoScenario,
    Document,
    EligibilityResult,
    EligibilityRule,
    Evidence,
    Opportunity,
    Policy,
    PolicyBenefit,
    PolicyChunk,
    PolicyScan,
    PolicyVersion,
    RequiredMaterial,
    Task,
    Tenant,
    ToolCall,
    Workflow,
    WorkflowRun,
)
from app.services.applications.artifacts import content_checksum

DATASET_VERSION = "investor-demo-2026.09.1"
DATA_CLASSIFICATION = "synthetic"


@dataclass(frozen=True)
class ScenarioSpec:
    key: str
    title: str
    company_name: str
    industry: str
    city: str
    persona: str
    summary: str
    opportunity: str
    policy_type: str
    authority: str
    article: str
    rule_quote: str
    benefit: str
    eligibility: str
    confidence: float
    missing: tuple[str, ...]
    ready_material: str
    missing_material: str
    next_best_action: str
    profile: dict


SCENARIOS = (
    ScenarioSpec(
        key="ai-software-compute-voucher",
        title="AI 软件企业 · 算力支持演示",
        company_name="DEMO · 云启 AI 软件示例企业",
        industry="人工智能软件",
        city="上海市",
        persona="成长型 AI 软件企业，正在扩大模型训练与推理投入",
        summary="展示资料解析、算力机会扫描、条件核验和缺口补齐。",
        opportunity="DEMO AI 企业算力券计划",
        policy_type="compute_voucher",
        authority="DEMO 政策发布机构（合成）",
        article="第三条",
        rule_quote="申报主体须为人工智能软件企业，并提供最近三个月合规算力使用凭证。",
        benefit="合成示例：按核验后投入的一定比例支持，不代表真实金额。",
        eligibility="POTENTIALLY_ELIGIBLE",
        confidence=0.82,
        missing=("最近三个月算力使用发票",),
        ready_material="企业营业执照（DEMO 摘要）",
        missing_material="最近三个月算力使用发票",
        next_best_action="补充最近三个月算力使用发票后重新执行资格核验。",
        profile={
            "company_scale": "50–99 人",
            "revenue_stage": "规模化增长",
            "funding_stage": "A 轮",
            "high_tech_status": "已认定（DEMO）",
            "core_products": ["企业知识智能平台", "模型推理服务"],
            "rd_summary": "研发人员占比约 48%（DEMO）",
            "intellectual_property": ["软件著作权 12 项（DEMO）"],
            "current_needs": ["算力成本优化", "政策申报"],
        },
    ),
    ScenarioSpec(
        key="advanced-manufacturing-specialized-sme",
        title="先进制造企业 · 专精特新演示",
        company_name="DEMO · 精工智造示例企业",
        industry="先进制造",
        city="苏州市",
        persona="具备细分市场产品和研发投入的制造企业",
        summary="展示结构化企业画像与硬门槛证据核验。",
        opportunity="DEMO 专精特新培育计划",
        policy_type="qualification",
        authority="DEMO 产业主管机构（合成）",
        article="第五条",
        rule_quote="申报企业须持续开展研发活动，拥有与核心产品相关的知识产权，并提交专项审计材料。",
        benefit="合成示例：进入培育库并获得后续服务资格，不代表真实政策权益。",
        eligibility="ELIGIBLE",
        confidence=0.93,
        missing=(),
        ready_material="知识产权清单（DEMO 摘要）",
        missing_material="专项审计材料更新版",
        next_best_action="进入申报材料人工复核，并确认专项审计材料的最新签章版本。",
        profile={
            "company_scale": "100–299 人",
            "revenue_stage": "稳定营收",
            "funding_stage": "未披露",
            "specialized_sme_status": "培育中（DEMO）",
            "core_products": ["精密运动控制模组"],
            "rd_summary": "设有独立研发中心（DEMO）",
            "intellectual_property": ["发明专利 8 项（DEMO）"],
            "current_needs": ["专精特新申报"],
        },
    ),
    ScenarioSpec(
        key="biomed-rd-program",
        title="生物医药企业 · 研发项目演示",
        company_name="DEMO · 澄明生物医药示例企业",
        industry="生物医药",
        city="杭州市",
        persona="处于产品验证阶段、材料完整性要求高的研发企业",
        summary="展示证据不足时系统返回 Need More Information，而非猜测结论。",
        opportunity="DEMO 生物医药研发项目",
        policy_type="research_program",
        authority="DEMO 科技项目机构（合成）",
        article="第六条",
        rule_quote="申报单位须提供研发项目立项证明、阶段性验证记录及研发费用归集说明。",
        benefit="合成示例：提供项目辅导和评审机会，不代表真实资助承诺。",
        eligibility="NEED_MORE_INFORMATION",
        confidence=0.61,
        missing=("阶段性验证记录", "研发费用归集说明"),
        ready_material="研发项目立项证明（DEMO 摘要）",
        missing_material="阶段性验证记录",
        next_best_action="上传阶段性验证记录和研发费用归集说明，再运行 Evidence Agent。",
        profile={
            "company_scale": "20–49 人",
            "revenue_stage": "产品验证",
            "funding_stage": "Pre-A 轮",
            "core_products": ["体外诊断候选产品"],
            "rd_summary": "核心研发团队已建立（DEMO）",
            "intellectual_property": ["专利申请 5 项（DEMO）"],
            "current_needs": ["研发项目申报", "材料完整性检查"],
        },
    ),
    ScenarioSpec(
        key="technology-services-digitalization",
        title="科技服务企业 · 数字化项目演示",
        company_name="DEMO · 远见科技服务示例企业",
        industry="科技服务",
        city="深圳市",
        persona="为产业客户交付数字化解决方案的服务企业",
        summary="展示机会匹配、服务合同证据和申报工作台。",
        opportunity="DEMO 产业数字化服务计划",
        policy_type="industry_program",
        authority="DEMO 数字经济机构（合成）",
        article="第四条",
        rule_quote="申报企业须具备可核验的产业数字化服务案例，并提供合同或验收材料。",
        benefit="合成示例：纳入服务商资源池，不代表真实采购或合作。",
        eligibility="POTENTIALLY_ELIGIBLE",
        confidence=0.79,
        missing=("一个项目的最终验收单",),
        ready_material="产业服务合同（DEMO 摘要）",
        missing_material="项目最终验收单",
        next_best_action="关联最近一个已交付项目的验收单，完成硬门槛校验。",
        profile={
            "company_scale": "50–99 人",
            "revenue_stage": "稳定营收",
            "funding_stage": "自筹",
            "tech_sme_status": "已入库（DEMO）",
            "core_products": ["产业数据治理服务", "智能运营解决方案"],
            "rd_summary": "平台研发与交付团队并行（DEMO）",
            "intellectual_property": ["软件著作权 18 项（DEMO）"],
            "current_needs": ["服务商入库", "案例材料核验"],
        },
    ),
    ScenarioSpec(
        key="startup-innovation-competition",
        title="初创企业 · 创新赛事演示",
        company_name="DEMO · 星途初创示例企业",
        industry="企业软件",
        city="成都市",
        persona="需要快速识别低成本市场与融资入口的早期团队",
        summary="展示从简版画像到赛事机会、材料清单和生成稿。",
        opportunity="DEMO 创新创业赛事",
        policy_type="competition",
        authority="DEMO 创新创业机构（合成）",
        article="第二条",
        rule_quote="参赛团队须处于早期发展阶段，提交商业计划书并说明核心产品与市场验证情况。",
        benefit="合成示例：获得展示与评审机会，不代表真实融资或获奖。",
        eligibility="ELIGIBLE",
        confidence=0.89,
        missing=(),
        ready_material="商业计划书初稿（DEMO 摘要）",
        missing_material="市场验证附件更新版",
        next_best_action="人工确认商业计划书关键数据后，导出 DOCX 进入提交准备。",
        profile={
            "company_scale": "1–19 人",
            "revenue_stage": "早期验证",
            "funding_stage": "天使轮",
            "core_products": ["企业协作自动化工具"],
            "rd_summary": "产品与工程团队共 8 人（DEMO）",
            "intellectual_property": ["软件著作权 2 项（DEMO）"],
            "current_needs": ["创新赛事", "融资机会"],
        },
    ),
)


def _get_or_create_agent(db: Session) -> Agent:
    agent = db.scalar(select(Agent).where(Agent.key == "demo_orchestrator", Agent.version == "1.0"))
    if agent:
        return agent
    agent = Agent(
        key="demo_orchestrator",
        name="Investor Demo Orchestrator",
        description="Deterministic, evidence-first synthetic demo trace.",
        version="1.0",
        status="active",
        input_schema_json={"type": "object", "required": ["company_id"]},
        output_schema_json={"type": "object", "required": ["opportunity_id", "verified"]},
    )
    db.add(agent)
    db.flush()
    return agent


def _get_or_create_workflow(db: Session) -> Workflow:
    workflow = db.scalar(
        select(Workflow).where(Workflow.key == "investor_demo_policy_workflow", Workflow.version == "1.0")
    )
    if workflow:
        return workflow
    workflow = Workflow(
        key="investor_demo_policy_workflow",
        name="Investor Demo Policy Workflow",
        version="1.0",
        status="active",
        definition_json={"steps": ["plan", "retrieve", "reason", "act", "verify", "finish"]},
    )
    db.add(workflow)
    db.flush()
    return workflow


def _seed_one(db: Session, spec: ScenarioSpec, *, display_order: int) -> DemoScenario:
    now = datetime.now(UTC)
    tenant = Tenant(
        name=spec.company_name,
        slug=f"demo-{spec.key}",
        is_active=True,
        account_stage="unclassified",
        is_demo=True,
        demo_dataset_key=spec.key,
    )
    db.add(tenant)
    db.flush()

    profile_snapshot = {
        "industry": spec.industry,
        "province": spec.city,
        "city": spec.city,
        "registered_address": f"{spec.city} DEMO 合成地址",
        "founded_date": "2022-01-01",
        "employee_count": None,
        "annual_revenue": None,
        "high_tech_status": "未提供",
        "tech_sme_status": "未提供",
        "specialized_sme_status": "未提供",
        "talent_summary": "关键岗位信息已抽取（DEMO）",
        "projects": [spec.opportunity],
        **spec.profile,
    }
    company = Company(
        tenant_id=tenant.id,
        name=spec.company_name,
        province=spec.city,
        city=spec.city,
        industry=spec.industry,
        metadata_json={"data_classification": DATA_CLASSIFICATION, "demo": True},
    )
    db.add(company)
    db.flush()
    profile = CompanyProfile(
        tenant_id=tenant.id,
        company_id=company.id,
        status="published",
        draft_json=profile_snapshot,
        completeness_score=86,
        published_version=1,
        published_at=now,
    )
    db.add(profile)
    db.flush()
    profile_version = CompanyProfileVersion(
        tenant_id=tenant.id,
        profile_id=profile.id,
        company_id=company.id,
        version=1,
        snapshot_json=profile_snapshot,
        completeness_score=86,
        published_at=now,
    )
    db.add(profile_version)
    document = Document(
        tenant_id=tenant.id,
        company_id=company.id,
        filename="DEMO_企业资料摘要.txt",
        content_type="text/plain",
        object_key=f"demo/{DATASET_VERSION}/{spec.key}/company-profile.txt",
        status="uploaded",
        size_bytes=1024,
        checksum_sha256=hashlib.sha256(spec.company_name.encode()).hexdigest(),
        metadata_json={
            "demo": True,
            "data_classification": DATA_CLASSIFICATION,
            "notice": "Synthetic metadata only; no customer file is stored.",
        },
        source_type="file",
        ingestion_status="completed",
        ingested_at=now,
    )
    db.add(document)
    db.flush()
    db.add_all(
        [
            CompanyFact(
                tenant_id=tenant.id,
                profile_version_id=profile_version.id,
                fact_key="industry",
                value_json={"value": spec.industry},
                source_document_id=document.id,
                confidence=0.98,
                extraction_method="deterministic_demo",
                verification_status="verified",
            ),
            CompanyFact(
                tenant_id=tenant.id,
                profile_version_id=profile_version.id,
                fact_key="city",
                value_json={"value": spec.city},
                source_document_id=document.id,
                confidence=0.98,
                extraction_method="deterministic_demo",
                verification_status="verified",
            ),
        ]
    )

    source_text = (
        "DEMO 合成政策原文。本文件仅用于产品演示，不对应任何真实政府文件、权益或申报承诺。\n"
        f"{spec.article}：{spec.rule_quote}\n"
        f"支持内容：{spec.benefit}\n"
        f"所需材料：{spec.ready_material}；{spec.missing_material}。"
    )
    policy = Policy(
        tenant_id=tenant.id,
        title=f"DEMO / 合成政策 · {spec.opportunity}",
        issuing_authority=spec.authority,
        level="demo",
        province=spec.city,
        city=spec.city,
        industry=spec.industry,
        policy_type=spec.policy_type,
        source_url=f"https://example.invalid/yance-demo/{spec.key}",
        jurisdiction=spec.city,
        published_at=now,
        effective_at=now,
        deadline=datetime(2026, 12, 31, tzinfo=UTC),
        content=source_text,
        original_text=source_text,
        summary=spec.summary,
        source="Yance synthetic investor demo",
        support_amount="DEMO：无真实金额",
        support_type="合成演示",
        status="published",
    )
    db.add(policy)
    db.flush()
    policy_version = PolicyVersion(
        policy_id=policy.id,
        tenant_id=tenant.id,
        version=1,
        content_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
        title=policy.title,
        issuer=spec.authority,
        region=spec.city,
        industry=spec.industry,
        policy_type=spec.policy_type,
        publish_date=now,
        effective_date=now,
        expiry_date=datetime(2026, 12, 31, tzinfo=UTC),
        source_url=policy.source_url,
        source_name="Yance synthetic investor demo",
        content=source_text,
        status="published",
    )
    db.add(policy_version)
    db.flush()
    quote_start = source_text.index(spec.rule_quote)
    chunk = PolicyChunk(
        policy_id=policy.id,
        policy_version_id=policy_version.id,
        tenant_id=tenant.id,
        chunk_index=0,
        article=spec.article,
        content=source_text,
        char_start=0,
        char_end=len(source_text),
        content_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
        metadata_json={"demo": True, "data_classification": DATA_CLASSIFICATION},
    )
    db.add(chunk)
    rule = EligibilityRule(
        policy_id=policy.id,
        policy_version_id=policy_version.id,
        tenant_id=tenant.id,
        name="DEMO 核心资格条件",
        fact_key="industry",
        operator="equals",
        expected_json={"value": spec.industry},
        is_hard_gate=True,
        source_quote=spec.rule_quote,
        article=spec.article,
        status="active",
    )
    db.add(rule)
    db.add_all(
        [
            RequiredMaterial(
                policy_id=policy.id,
                policy_version_id=policy_version.id,
                tenant_id=tenant.id,
                name=spec.ready_material,
                description="已从 DEMO 企业资料摘要中识别。",
                is_hard_gate=True,
                source_quote=spec.rule_quote,
                article=spec.article,
            ),
            RequiredMaterial(
                policy_id=policy.id,
                policy_version_id=policy_version.id,
                tenant_id=tenant.id,
                name=spec.missing_material,
                description="需要用户补齐或确认。",
                is_hard_gate=True,
                source_quote=spec.rule_quote,
                article=spec.article,
            ),
            PolicyBenefit(
                policy_id=policy.id,
                policy_version_id=policy_version.id,
                tenant_id=tenant.id,
                benefit_type="demo",
                description=spec.benefit,
                amount_text="DEMO：无真实金额",
                source_quote=spec.rule_quote,
                article=spec.article,
            ),
        ]
    )

    workflow = _get_or_create_workflow(db)
    agent = _get_or_create_agent(db)
    workflow_run = WorkflowRun(
        tenant_id=tenant.id,
        workflow_id=workflow.id,
        company_id=company.id,
        status="completed",
        current_step="finish",
        input_json={"company_id": str(company.id), "demo": True},
        output_json={"verified": True, "eligibility": spec.eligibility},
        input_tokens=0,
        output_tokens=0,
        cost_usd=0,
        latency_ms=1430,
        started_at=now,
        finished_at=now,
    )
    db.add(workflow_run)
    db.flush()
    scan = PolicyScan(
        tenant_id=tenant.id,
        company_id=company.id,
        profile_version_id=profile_version.id,
        workflow_run_id=workflow_run.id,
        idempotency_key=f"demo:{DATASET_VERSION}:{spec.key}",
        status="completed",
        provider="deterministic_demo",
        total_opportunities=1,
        started_at=now,
        completed_at=now,
    )
    db.add(scan)
    db.flush()
    opportunity = Opportunity(
        tenant_id=tenant.id,
        company_id=company.id,
        policy_id=policy.id,
        policy_version_id=policy_version.id,
        title=spec.opportunity,
        score=round(spec.confidence * 100, 1),
        status="identified",
        evidence_json={"count": 1, "verified": True, "demo": True},
        scan_id=scan.id,
        profile_version_id=profile_version.id,
        policy_snapshot_json={
            "title": policy.title,
            "issuer": spec.authority,
            "region": spec.city,
            "deadline": "2026-12-31",
            "data_classification": DATA_CLASSIFICATION,
        },
        eligibility_status=spec.eligibility,
        eligibility_confidence=spec.confidence,
    )
    db.add(opportunity)
    db.flush()
    criteria = [
        {
            "name": "行业匹配",
            "status": "met",
            "expected": spec.industry,
            "actual": spec.industry,
            "hard_gate": True,
        },
        {
            "name": spec.missing_material,
            "status": "met" if not spec.missing else "missing",
            "expected": "已提供且可核验",
            "actual": "已提供" if not spec.missing else "未提供",
            "hard_gate": True,
        },
    ]
    eligibility = EligibilityResult(
        tenant_id=tenant.id,
        opportunity_id=opportunity.id,
        policy_version_id=policy_version.id,
        profile_version_id=profile_version.id,
        status=spec.eligibility,
        confidence=spec.confidence,
        summary=f"{spec.eligibility}：结论由结构化规则与精确引用共同支持。",
        criteria_json=criteria,
        missing_information_json=list(spec.missing),
        engine_version="deterministic-demo-v1",
        review_status="system_verified",
        verified_at=now,
    )
    db.add(eligibility)
    db.flush()
    evidence = Evidence(
        tenant_id=tenant.id,
        opportunity_id=opportunity.id,
        eligibility_result_id=eligibility.id,
        policy_version_id=policy_version.id,
        policy_chunk_id=chunk.id,
        eligibility_rule_id=rule.id,
        source_title=policy.title,
        source_url=policy.source_url,
        issuer=spec.authority,
        article=spec.article,
        quote=spec.rule_quote,
        quote_start=quote_start,
        quote_end=quote_start + len(spec.rule_quote),
        confidence=1,
        verifier="exact_span_v1",
        verified=True,
    )
    db.add(evidence)

    application = Application(
        tenant_id=tenant.id,
        company_id=company.id,
        opportunity_id=opportunity.id,
        title=f"{spec.opportunity} · 申报工作区",
        status="in_progress",
        form_data={"demo": True, "data_classification": DATA_CLASSIFICATION},
        due_at=datetime(2026, 12, 31, tzinfo=UTC),
        progress=72 if spec.missing else 88,
        review_status="review_required",
    )
    db.add(application)
    db.flush()
    ready_req = ApplicationRequirement(
        tenant_id=tenant.id,
        application_id=application.id,
        title=spec.ready_material,
        description="已关联到 DEMO 企业资料摘要。",
        category="material",
        status="ready",
        is_hard_gate=True,
        source_json={"policy_version_id": str(policy_version.id), "article": spec.article},
        sort_order=1,
    )
    missing_req = ApplicationRequirement(
        tenant_id=tenant.id,
        application_id=application.id,
        title=spec.missing_material,
        description="需要补齐或由人工确认的材料。",
        category="material",
        status="missing" if spec.missing else "review",
        is_hard_gate=True,
        source_json={"policy_version_id": str(policy_version.id), "article": spec.article},
        sort_order=2,
    )
    db.add_all([ready_req, missing_req])
    db.flush()
    db.add(
        ApplicationDocumentLink(
            tenant_id=tenant.id,
            application_id=application.id,
            document_id=document.id,
            requirement_id=ready_req.id,
            status="linked",
        )
    )
    db.add(
        ApplicationActivity(
            tenant_id=tenant.id,
            application_id=application.id,
            action="demo_workspace_created",
            summary="系统根据已核验机会创建 DEMO 申报工作区。",
            metadata_json={"demo": True, "synthetic": True},
            occurred_at=now,
        )
    )
    task = Task(
        tenant_id=tenant.id,
        company_id=company.id,
        application_id=application.id,
        scan_id=scan.id,
        task_type="application_material_review",
        title=f"检查并完善：{spec.missing_material}",
        description=spec.next_best_action,
        input_data={"requirement_id": str(missing_req.id), "demo": True},
        metadata_json={"data_classification": DATA_CLASSIFICATION},
        status="completed" if not spec.missing else "ready",
        priority="high" if spec.missing else "normal",
        agent_type="ApplicationAgent",
        workflow_version="1.0",
        model_provider="deterministic",
        model_name="evidence-template-v1",
        payment_status="not_applicable",
        review_status="review_required",
        progress=100 if not spec.missing else 20,
        current_stage="human_review" if not spec.missing else "material_gap",
    )
    db.add(task)
    db.flush()
    scan.task_id = task.id
    workflow_run.task_id = task.id

    run = AgentRun(
        tenant_id=tenant.id,
        task_id=task.id,
        agent_id=agent.id,
        workflow_run_id=workflow_run.id,
        agent_name="Orchestrator Agent",
        provider="deterministic",
        model="evidence-template-v1",
        prompt_version="demo-1.0",
        status="completed",
        input_json={"company_id": str(company.id), "profile_version_id": str(profile_version.id)},
        output_json={
            "opportunity_id": str(opportunity.id),
            "eligibility": spec.eligibility,
            "verified": True,
        },
        started_at=now,
        finished_at=now,
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        cost_usd=0,
        latency_ms=1430,
        retry_count=0,
        max_retries=2,
        metadata_json={"demo": True, "data_classification": DATA_CLASSIFICATION},
    )
    db.add(run)
    db.flush()
    step_outputs = {
        "plan": {"plan": ["retrieve", "eligibility", "evidence", "application"]},
        "retrieve": {"policy_version_id": str(policy_version.id), "result_count": 1},
        "reason": {"eligibility": spec.eligibility, "criteria_count": len(criteria)},
        "act": {"application_id": str(application.id)},
        "verify": {"citation_exact": True, "tenant_consistent": True},
        "finish": {"next_best_action": spec.next_best_action},
    }
    steps: list[AgentStep] = []
    for sequence, step_type in enumerate(step_outputs, start=1):
        step = AgentStep(
            tenant_id=tenant.id,
            agent_run_id=run.id,
            agent_id=agent.id,
            sequence=sequence,
            step_type=step_type,
            status="completed",
            input_json={"demo": True},
            output_json=step_outputs[step_type],
            verification_json={"passed": True} if step_type == "verify" else {},
            input_tokens=0,
            output_tokens=0,
            cost_usd=0,
            latency_ms=200,
            started_at=now,
            finished_at=now,
        )
        db.add(step)
        steps.append(step)
    db.flush()
    db.add(
        ToolCall(
            tenant_id=tenant.id,
            agent_run_id=run.id,
            agent_step_id=steps[1].id,
            tool_name="hybrid_policy_search",
            idempotency_key=f"demo-search:{spec.key}",
            status="completed",
            arguments_json={"industry": spec.industry, "region": spec.city, "demo": True},
            result_json={"policy_version_id": str(policy_version.id), "result_count": 1},
            latency_ms=120,
            started_at=now,
            finished_at=now,
        )
    )

    artifact_content = {
        "title": f"{spec.opportunity} · 申报工作稿（DEMO）",
        "company_name": spec.company_name,
        "executive_summary": spec.summary,
        "eligibility": {"status": spec.eligibility, "summary": eligibility.summary},
        "criteria": criteria,
        "requirements": [
            {"title": ready_req.title, "description": ready_req.description, "status": ready_req.status},
            {"title": missing_req.title, "description": missing_req.description, "status": missing_req.status},
        ],
        "evidence": [
            {
                "source_title": evidence.source_title,
                "article": evidence.article,
                "quote": evidence.quote,
                "verified": evidence.verified,
                "source_url": evidence.source_url,
            }
        ],
        "next_best_action": spec.next_best_action,
        "data_notice": "DEMO synthetic example. Human review is required before any real submission.",
    }
    artifact = ApplicationArtifact(
        tenant_id=tenant.id,
        application_id=application.id,
        artifact_type="application_brief",
        title=artifact_content["title"],
        version=1,
        status="draft",
        generation_method="deterministic-evidence-v1",
        content_json=artifact_content,
        source_snapshot_json={
            "profile_version_id": str(profile_version.id),
            "policy_version_id": str(policy_version.id),
            "eligibility_result_id": str(eligibility.id),
            "evidence_ids": [str(evidence.id)],
            "demo": True,
        },
        checksum_sha256=content_checksum(artifact_content),
        review_note="DEMO synthetic draft; not approved for real submission.",
    )
    db.add(artifact)
    db.flush()

    scenario = DemoScenario(
        key=spec.key,
        tenant_id=tenant.id,
        company_id=company.id,
        profile_version_id=profile_version.id,
        document_id=document.id,
        scan_id=scan.id,
        opportunity_id=opportunity.id,
        eligibility_result_id=eligibility.id,
        application_id=application.id,
        artifact_id=artifact.id,
        agent_run_id=run.id,
        title=spec.title,
        industry=spec.industry,
        persona=spec.persona,
        summary=spec.summary,
        next_best_action=spec.next_best_action,
        dataset_version=DATASET_VERSION,
        data_classification=DATA_CLASSIFICATION,
        status="published",
        display_order=display_order,
    )
    db.add(scenario)
    db.flush()
    return scenario


def seed_investor_demo(db: Session, *, replace: bool = False) -> list[DemoScenario]:
    """Create the isolated synthetic dataset; never mutates real tenants or commerce data."""

    keys = [spec.key for spec in SCENARIOS]
    existing = db.scalars(
        select(DemoScenario).where(DemoScenario.key.in_(keys)).order_by(DemoScenario.display_order)
    ).all()
    if existing and not replace:
        if len(existing) != len(SCENARIOS) or any(
            item.dataset_version != DATASET_VERSION for item in existing
        ):
            raise RuntimeError("Partial or outdated demo dataset found; rerun with replace=True.")
        return existing
    if replace:
        demo_tenants = db.scalars(
            select(Tenant).where(Tenant.is_demo.is_(True), Tenant.demo_dataset_key.in_(keys))
        ).all()
        if demo_tenants:
            db.execute(delete(Tenant).where(Tenant.id.in_([item.id for item in demo_tenants])))
            db.flush()

    scenarios = [
        _seed_one(db, spec, display_order=index)
        for index, spec in enumerate(SCENARIOS, start=1)
    ]
    db.commit()
    return scenarios
