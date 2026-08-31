"""Policy Evaluation Engine — Evidence-Grounded 资格判定
User Input → Extract Criteria → Evaluate Each → Evidence Gate → Result
"""
import json
import re
from datetime import datetime, timezone

from app.services.llm.router import LLMRouter
from app.services.llm.base import LLMRequest
from app.services.policy_engine.schemas import (
    CriteriaExtraction, EligibilityJudgment, PolicyEvaluationResult,
    CriterionResult, OverallResult, CriterionEvaluation,
    EvidenceItem, MissingMaterial, RiskItem, NextBestAction,
)

_llm = LLMRouter()


# ── Step 1: Extract hard criteria from policy text ───────────
async def extract_criteria(policy_content: str, provider: str = "deepseek") -> list[dict]:
    prompt = f"""你是政策申报条件提取专家。从以下政策原文中提取所有硬性申报条件（资格门槛）。

政策原文：
{policy_content[:3000]}

要求：
1. 只提取明确写出的硬性条件（如注册资本、成立年限、知识产权数量、研发费用占比、企业规模、行业限制等）
2. 每个条件必须附上原文引用（policy_quote）
3. 输出 JSON 格式
4. 不确定的不要编造

输出 JSON：{{"criteria": [{{"criterion": "条件描述", "policy_quote": "原文引用"}}]}}"""

    try:
        import asyncio
        response = await asyncio.wait_for(
            _llm.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model="deepseek-chat" if provider == "deepseek" else "qwen-plus",
                temperature=0.1, max_tokens=2000,
            ), provider=provider),
            timeout=30,
        )
        parsed = json.loads(response.content)
        return parsed.get("criteria", [])
    except Exception:
        # Fallback: 提取关键词句子
        sentences = re.split(r'[。；！？\n]', policy_content)
        criteria = []
        keywords = ["注册", "成立", "资本", "知识产权", "专利", "软著", "研发", "收入", "营收", "规模", "人员", "比例", "占比", "认定", "资质", "行业", "领域"]
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and any(kw in s for kw in keywords):
                criteria.append({"criterion": s[:200], "policy_quote": s[:200]})
        return criteria[:10]


# ── Step 2: Evaluate each criterion against company profile ──
async def evaluate_criteria(
    criteria: list[dict],
    company_name: str,
    company_profile: dict,
    provider: str = "deepseek",
) -> EligibilityJudgment:
    profile_text = json.dumps(company_profile, ensure_ascii=False, indent=2)[:2000]
    criteria_text = json.dumps(criteria, ensure_ascii=False, indent=2)[:2000]

    prompt = f"""你是政策申报资格判定专家。根据企业画像逐项判定是否满足政策硬性条件。

企业名称：{company_name}
企业画像：{profile_text}

政策硬性条件：
{criteria_text}

判定规则：
- PASS：企业数据明确满足该条件
- FAIL：企业数据明确不满足该条件
- INSUFFICIENT：企业数据不足，无法判断

每个条件必须给出：
1. 企业对应的事实（enterprise_fact）
2. 判定结果（result: PASS/FAIL/INSUFFICIENT）
3. 判定理由（reason）
4. 如果 INSUFFICIENT，说明缺什么信息（missing_information）

输出 JSON：
{{"criteria": [{{"criterion": "", "enterprise_fact": "", "policy_requirement": "", "result": "PASS|FAIL|INSUFFICIENT", "reason": "", "missing_information": "", "confidence": 0.8}}], "overall_result": "ELIGIBLE|NOT_ELIGIBLE|INSUFFICIENT_INFO", "summary": ""}}

overall_result 规则：
- 如果任何条件为 FAIL → NOT_ELIGIBLE
- 如果没有 FAIL 但有 INSUFFICIENT → INSUFFICIENT_INFO
- 如果全部 PASS → ELIGIBLE"""

    try:
        import asyncio
        response = await asyncio.wait_for(
            _llm.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model="deepseek-chat" if provider == "deepseek" else "qwen-plus",
                temperature=0.1, max_tokens=3000,
            ), provider=provider),
            timeout=45,
        )
        parsed = json.loads(response.content)
        criteria_results = []
        for c in parsed.get("criteria", []):
            result_str = c.get("result", "INSUFFICIENT").upper()
            if result_str not in ("PASS", "FAIL", "INSUFFICIENT"):
                result_str = "INSUFFICIENT"
            criteria_results.append(CriterionEvaluation(
                criterion=c.get("criterion", ""),
                enterprise_fact=c.get("enterprise_fact", ""),
                policy_requirement=c.get("policy_requirement", ""),
                evidence_quote=c.get("policy_requirement", ""),
                evidence_source="政策原文",
                result=CriterionResult(result_str),
                reason=c.get("reason", ""),
                missing_information=c.get("missing_information", ""),
                confidence=min(max(float(c.get("confidence", 0.5)), 0), 1),
            ))
        overall = parsed.get("overall_result", "INSUFFICIENT_INFO").upper()
        if overall not in ("ELIGIBLE", "NOT_ELIGIBLE", "INSUFFICIENT_INFO"):
            overall = "INSUFFICIENT_INFO"
        return EligibilityJudgment(
            criteria=criteria_results,
            overall_result=OverallResult(overall),
            summary=parsed.get("summary", ""),
        )
    except json.JSONDecodeError:
        # Retry with simpler prompt
        return _fallback_evaluation(criteria, company_profile)
    except Exception:
        return _fallback_evaluation(criteria, company_profile)


def _fallback_evaluation(criteria, company_profile) -> EligibilityJudgment:
    """No-LLM fallback: basic keyword matching"""
    results = []
    profile_str = json.dumps(company_profile, ensure_ascii=False).lower()
    fails = 0
    insufficient = 0
    for c in criteria:
        crit = c.get("criterion", "")
        found = any(kw in profile_str for kw in ["是", "有", "已", "获得"] if kw in crit.lower())
        if found:
            results.append(CriterionEvaluation(criterion=crit, enterprise_fact="见企业画像", policy_requirement=crit, result=CriterionResult.PASS, reason="基于企业画像关键词匹配", confidence=0.5))
        else:
            results.append(CriterionEvaluation(criterion=crit, enterprise_fact="数据不足", policy_requirement=crit, result=CriterionResult.INSUFFICIENT, reason="企业画像中未找到对应数据", missing_information="需补充相关企业信息", confidence=0.3))
            insufficient += 1
    if fails > 0:
        overall = OverallResult.NOT_ELIGIBLE
    elif insufficient > 0:
        overall = OverallResult.INSUFFICIENT_INFO
    else:
        overall = OverallResult.ELIGIBLE
    return EligibilityJudgment(criteria=results, overall_result=overall, summary="基于关键词匹配的基础判定")


# ── Step 3: Evidence Gate ────────────────────────────────────
def validate_evidence(result: EligibilityJudgment, policy_content: str) -> tuple[EligibilityJudgment, list[str]]:
    """验证 LLM 输出中的关键事实是否能追溯到政策原文。
    返回 (修正后的结果, 被拦截的幻觉列表)
    """
    hallucinations = []
    # 提取政策原文中的关键数字
    policy_numbers = set(re.findall(r'\d+(?:\.\d+)?(?:%|万|亿|年|个月|天|人|项|件)', policy_content))
    
    for criterion in result.criteria:
        reason = criterion.reason
        # 检查 reason 中是否包含政策原文中不存在的数字
        reason_numbers = set(re.findall(r'\d+(?:\.\d+)?(?:%|万|亿|年|个月|天|人|项|件)', reason))
        unsupported = reason_numbers - policy_numbers
        if unsupported:
            for num in unsupported:
                if num not in policy_content:
                    hallucinations.append(f"条件 [{criterion.criterion[:30]}] 中引用了政策原文中不存在的数字: {num}")
                    criterion.reason = reason.replace(num, "[数据待验证]")
                    criterion.confidence = min(criterion.confidence, 0.3)
    
    return result, hallucinations


# ── Step 4: Generate missing materials + risks + next actions ─
def generate_recommendations(result: EligibilityJudgment, policy_title: str) -> tuple[list, list, list]:
    missing_materials = []
    risks = []
    next_actions = []
    
    for c in result.criteria:
        if c.result == CriterionResult.INSUFFICIENT and c.missing_information:
            missing_materials.append(MissingMaterial(material=c.missing_information, reason=c.reason))
        if c.result == CriterionResult.FAIL:
            risks.append(RiskItem(risk=f"不满足条件: {c.criterion[:50]}", severity="high", mitigation=f"需补齐: {c.missing_information or c.reason}"))
    
    if result.overall_result == OverallResult.INSUFFICIENT_INFO:
        next_actions.append(NextBestAction(action="完善企业画像", description="补充缺失信息以获得准确判定", cta="更新画像"))
    if result.overall_result == OverallResult.ELIGIBLE:
        next_actions.append(NextBestAction(action="生成申报材料", description=f"企业符合 {policy_title} 申报条件，建议启动申报", product_code="APPLICATION_PLAN", cta="生成方案 ¥699"))
    if missing_materials:
        next_actions.append(NextBestAction(action="生成材料清单", description=f"共 {len(missing_materials)} 项材料需要准备", cta="查看清单"))
    
    return missing_materials, risks, next_actions


# ── Main Entry Point ─────────────────────────────────────────
async def evaluate_policy(
    policy_id: str,
    policy_title: str,
    policy_content: str,
    policy_level: str,
    company_name: str,
    company_profile: dict,
    provider: str = "deepseek",
) -> PolicyEvaluationResult:
    start = datetime.now(timezone.utc)
    
    # Step 1: Extract criteria
    criteria = await extract_criteria(policy_content, provider)
    if not criteria:
        return PolicyEvaluationResult(
            overall_result=OverallResult.INSUFFICIENT_INFO,
            matched_policy_title=policy_title,
            summary="政策内容为空或过短，无法提取申报条件。",
        )
    
    # Step 2: Evaluate each criterion
    judgment = await evaluate_criteria(criteria, company_name, company_profile, provider)
    
    # Step 3: Evidence Gate
    judgment, hallucinations = validate_evidence(judgment, policy_content)
    
    # Step 4: Generate recommendations
    missing_materials, risks, next_actions = generate_recommendations(judgment, policy_title)
    
    # Build evidence items from policy
    evidence = [EvidenceItem(
        source_title=policy_title,
        publisher="政府发布",
        quote=c.get("policy_quote", "")[:200],
        confidence=0.9,
    ) for c in criteria[:5]]
    
    end = datetime.now(timezone.utc)
    latency = int((end - start).total_seconds() * 1000)
    
    hard_failures = [c.criterion for c in judgment.criteria if c.result == CriterionResult.FAIL]
    missing_info = [c.missing_information for c in judgment.criteria if c.result == CriterionResult.INSUFFICIENT and c.missing_information]
    
    return PolicyEvaluationResult(
        overall_result=judgment.overall_result,
        matched_policy_id=policy_id,
        matched_policy_title=policy_title,
        criteria=judgment.criteria,
        hard_failures=hard_failures,
        missing_information=missing_info,
        missing_materials=missing_materials,
        risks=risks,
        next_best_actions=next_actions,
        evidence=evidence,
        summary=judgment.summary or f"针对 {policy_title} 的资格判定结果：{judgment.overall_result.value}",
        model_metadata={
            "provider": provider,
            "latency_ms": latency,
            "policy_level": policy_level,
            "hallucinations_blocked": len(hallucinations),
            "criteria_count": len(criteria),
        },
    )
