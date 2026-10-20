"""Policy Evaluation Engine V2.1 — Evidence-Grounded 资格判定
Flow: Policy text → extract criteria → normalize → match facts
      → deterministic / semantic evaluation → Evidence Gate → Final Eligibility Gate → output
V2.1 变更（benchmark/V21_AUDIT.md）：
  D1 deterministic evaluator 交叉验证（程序优先）
  D2 Evidence Gate 只校验门槛断言，企业事实数字豁免
  D3 Final Eligibility Gate 程序化聚合（LLM 无权绕过）
  D4 政策窗口 6000 字
  D5 temperature=0
  D6 fallback 保守化：绝不输出 PASS
  D7 Enterprise Fact Normalization
  D8 条件结构化（field/operator/value）
"""
# ruff: noqa: E501 -- domain prompts preserve policy wording and JSON examples.

import asyncio
import json
import re
from datetime import UTC, datetime

from app.services.llm.base import LLMRequest
from app.services.llm.router import LLMRouter
from app.services.policies.eligibility import exact_quote_span
from app.services.policy_engine.deterministic import (
    _is_blocking,
    evaluate_deterministic,
    final_gate,
    normalize_criteria,
    normalize_facts,
)
from app.services.policy_engine.schemas import (
    CriterionEvaluation,
    CriterionResult,
    EligibilityJudgment,
    EvidenceItem,
    MissingMaterial,
    NextBestAction,
    OverallResult,
    PolicyEvaluationResult,
    RiskItem,
)

_llm = LLMRouter()

ENGINE_VERSION = "policy-engine-v2.3-evidence-gate"
PROMPT_VERSION = "PE-PROMPT-v2.1"


def _loads_json(text: str) -> dict:
    """鲁棒解析 LLM 输出 JSON（修复 D-codeblock）：
    剥离 ```json 代码块、前后自然语言，截取首个完整 {...} 或 [...] 对象。
    解析失败抛异常，交给上层 fallback（绝不在本函数内静默吞错）。
    """
    if not text:
        raise ValueError("empty LLM content")
    t = text.strip()
    # 1) 剥离 markdown 代码块（```json ... ``` 或 ``` ... ```）
    if "```" in t:
        segs = t.split("```")
        for seg in segs[1:]:
            seg = seg.strip()
            if seg.lower().startswith("json"):
                seg = seg[4:].strip()
            if seg[:1] in ("{", "["):
                t = seg
                break
        else:
            t = t.replace("```", "")
    # 2) 截取首个平衡的 {…} / […]
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s = t.find(open_c)
        if s != -1:
            depth = 0
            for i in range(s, len(t)):
                if t[i] == open_c:
                    depth += 1
                elif t[i] == close_c:
                    depth -= 1
                    if depth == 0:
                        return json.loads(t[s : i + 1])
    # 3) 兜底：整串直解（可能含前后空格/回车）
    return json.loads(t.strip())


def _usage_of(resp) -> dict:
    u = getattr(resp, "usage", None) or {}
    return {
        "input_tokens": u.get("prompt_tokens", "NOT_AVAILABLE"),
        "output_tokens": u.get("completion_tokens", "NOT_AVAILABLE"),
        "cached_tokens": (
            u.get("prompt_cache_hit_tokens", "NOT_AVAILABLE")
            if isinstance(u, dict)
            else "NOT_AVAILABLE"
        ),
    }


# ── Step 1: Extract hard criteria from policy text ───────────
async def extract_criteria(policy_content: str, provider: str = "deepseek") -> list[dict]:
    window = policy_content[:6000]
    prompt = f"""你是政策申报条件提取专家。从以下政策原文中提取所有硬性申报条件（资格门槛）。

政策原文：
{window}

要求：
1. 只提取明确写出的硬性条件（如成立年限、知识产权、研发费用占比、企业规模、人员占比、收入区间、资质要求等）
2. 一个条件句里若有多个并列量化要求（如"从业人员不超过500人、销售收入不超过2亿元、资产总额不超过2亿元"），必须拆成多个独立条件
3. 每个条件必须附上原文引用（policy_quote），逐字摘录
4. 不确定的不要编造；禁止使用原文之外的知识补充条件

输出 JSON：{{"criteria": [{{"criterion": "条件描述", "policy_quote": "原文引用"}}]}}"""

    try:
        response = await asyncio.wait_for(
            _llm.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    model="deepseek-chat" if provider == "deepseek" else "qwen-plus",
                    temperature=0,
                    max_tokens=3000,
                ),
                provider=provider,
            ),
            timeout=60,
        )
        parsed = _loads_json(response.content)
        return parsed.get("criteria", [])
    except Exception:
        # Fallback: 关键词句子提取（保守，只提取不判定）
        sentences = re.split(r"[。；！？\n]", policy_content)
        criteria = []
        keywords = [
            "注册",
            "成立",
            "资本",
            "知识产权",
            "专利",
            "软著",
            "研发",
            "收入",
            "营收",
            "规模",
            "人员",
            "比例",
            "占比",
            "认定",
            "资质",
            "行业",
            "领域",
            "细分市场",
        ]
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and any(kw in s for kw in keywords):
                criteria.append({"criterion": s[:200], "policy_quote": s[:200]})
        return criteria[:12]


# ── Step 2: Evaluate each criterion ──────────────────────────
async def evaluate_criteria(
    criteria: list[dict],
    company_name: str,
    company_profile: dict,
    provider: str = "deepseek",
) -> tuple[EligibilityJudgment, dict]:
    """返回 (判定, telemetry)。只对 semantic 类条件调用 LLM；numeric 类已由程序判定。"""
    profile_text = json.dumps(company_profile, ensure_ascii=False, indent=2)[:2500]
    criteria_text = json.dumps(criteria, ensure_ascii=False, indent=2)[:2500]

    prompt = f"""你是政策申报资格判定专家。根据企业画像逐项判定是否满足政策硬性条件。

企业名称：{company_name}
企业画像：{profile_text}

政策硬性条件：
{criteria_text}

判定规则：
- PASS：企业数据明确满足该条件
- FAIL：企业数据明确不满足该条件
- INSUFFICIENT：仅当完成判断所必需的企业事实在画像中确实缺失时才可使用；画像中已有的数据必须直接使用，不得因字段命名或表述差异而判 INSUFFICIENT
- 禁止猜测画像中不存在的数据；禁止使用你自己的政策知识补充要求，只能依据上面列出的条件判定
- 需要计算时给出计算过程（在 reason 中写明分子/分母）

每个条件必须给出：enterprise_fact（企业事实）、result（PASS/FAIL/INSUFFICIENT）、reason（判定理由，含计算）、INSUFFICIENT 时说明 missing_information

输出 JSON：
{{"criteria": [{{"criterion": "", "enterprise_fact": "", "policy_requirement": "", "result": "PASS|FAIL|INSUFFICIENT", "reason": "", "missing_information": "", "confidence": 0.8}}], "summary": ""}}"""

    telemetry = {
        "llm_call_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "tokens_available": False,
    }
    try:
        response = await asyncio.wait_for(
            _llm.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    model="deepseek-chat" if provider == "deepseek" else "qwen-plus",
                    temperature=0,
                    max_tokens=4000,
                ),
                provider=provider,
            ),
            timeout=90,
        )
        telemetry["llm_call_count"] = 1
        u = _usage_of(response)
        if u["input_tokens"] != "NOT_AVAILABLE":
            telemetry["tokens_available"] = True
            telemetry["input_tokens"] = u["input_tokens"]
            telemetry["output_tokens"] = u["output_tokens"]
            telemetry["cached_tokens"] = u["cached_tokens"]
        parsed = _loads_json(response.content)
        criteria_results = []
        by_criterion = {}
        for c in parsed.get("criteria", []):
            result_str = str(c.get("result", "INSUFFICIENT")).upper()
            if result_str not in ("PASS", "FAIL", "INSUFFICIENT"):
                result_str = "INSUFFICIENT"
            ce = CriterionEvaluation(
                criterion=c.get("criterion", ""),
                enterprise_fact=c.get("enterprise_fact", ""),
                policy_requirement=c.get("policy_requirement", ""),
                evidence_quote=c.get("policy_requirement", ""),
                evidence_source="政策原文",
                result=CriterionResult(result_str),
                reason=c.get("reason", ""),
                missing_information=c.get("missing_information", ""),
                confidence=min(max(float(c.get("confidence", 0.5)), 0), 1),
            )
            criteria_results.append(ce)
            by_criterion[ce.criterion] = ce
        return EligibilityJudgment(
            criteria=criteria_results,
            overall_result=OverallResult.INSUFFICIENT_INFO,
            summary=parsed.get("summary", ""),
        ), telemetry
    except Exception as e:
        # D6: fallback 保守化 —— 永不输出 PASS
        results = []
        for c in criteria:
            results.append(
                CriterionEvaluation(
                    criterion=c.get("criterion", ""),
                    enterprise_fact="数据不足",
                    policy_requirement=c.get("policy_quote", ""),
                    result=CriterionResult.INSUFFICIENT,
                    reason="引擎判定通道异常，保守标记为信息不足",
                    missing_information="需人工复核",
                    confidence=0.1,
                )
            )
        return EligibilityJudgment(
            criteria=results,
            overall_result=OverallResult.INSUFFICIENT_INFO,
            summary="fallback保守判定",
        ), {**telemetry, "error": str(e)[:200]}


# ── Step 3: Evidence Gate（V2.1 精准化）────────────────────────
def validate_evidence(
    result: EligibilityJudgment, policy_content: str
) -> tuple[EligibilityJudgment, list[str]]:
    """只校验「政策门槛断言」：policy_requirement / policy_quote 中出现、且不在 frozen policy
    全文中的比例/金额/分数类数字 → 记幻觉并降级为 INSUFFICIENT。
    enterprise_fact / reason 中的企业自身数字一律豁免（V2.1 修复 D2）。
    V2.2 修复：数字比较前先去除千分位逗号（"5,000万"=="5000万"），否则逗号格式差异会导致
    合法政策数字被误判为幻觉（V2.1 中 46 次误杀的根因）。
    """
    hallucinations = []
    full = policy_content[:12000]
    full_norm = re.sub(r",(?=\d)", "", full)  # 去千分位逗号

    def _norm_field(s: str) -> str:
        return re.sub(r",(?=\d)", "", s or "")

    for criterion in result.criteria:
        # Numbers appearing somewhere in the document do not support a claim.
        # Both the actual requirement and its quote must be literal source spans.
        # Normalize only thousands separators, not comparators or region names.
        fields = [criterion.policy_requirement, criterion.evidence_quote]
        if any(not field or exact_quote_span(full_norm, _norm_field(field)) is None for field in fields):
            hallucinations.append(f"条件 [{criterion.criterion[:30]}] 缺少逐字支持要求的原文引用")
            criterion.result = CriterionResult.INSUFFICIENT
            criterion.reason = (criterion.reason or "") + "｜[Evidence Gate] 引用未获原文逐字支持，需人工复核"
            criterion.missing_information = "请补充支持该条件的政策原文条款并人工复核"
            criterion.confidence = min(criterion.confidence, 0.3)
        checked_fields = [criterion.policy_requirement or "", criterion.evidence_quote or ""]
        for field in checked_fields:
            fn = _norm_field(field)
            nums = set(re.findall(r"\d+(?:\.\d+)?(?:%|％|万|亿|分)", fn))
            unsupported = {n for n in nums if exact_quote_span(full_norm, n) is None}
            if unsupported:
                hallucinations.append(
                    f"条件 [{criterion.criterion[:30]}] 的要求引用了政策原文中不存在的数值: {sorted(unsupported)}"
                )
                criterion.result = CriterionResult.INSUFFICIENT
                criterion.reason = (
                    criterion.reason or ""
                ) + "｜[Evidence Gate] 政策要求含未经原文支持的数值，降级为信息不足"
                criterion.confidence = min(criterion.confidence, 0.3)
    return result, hallucinations


# ── Step 3.5: Logic Validator ────────────────────────────────
def logic_validate(judgment: EligibilityJudgment) -> list[str]:
    """程序校验（V21_AUDIT 第九节）。返回校验失败清单。"""
    failures = []
    has_fail = any(c.result == CriterionResult.FAIL for c in judgment.criteria)
    has_insuff = any(c.result == CriterionResult.INSUFFICIENT for c in judgment.criteria)
    if has_fail and judgment.overall_result == OverallResult.ELIGIBLE:
        failures.append(
            "LOGIC_CONFLICT: criteria 存在 FAIL 但 overall=ELIGIBLE（已由 Final Gate 纠正）"
        )
    if has_insuff and judgment.overall_result == OverallResult.ELIGIBLE and not has_fail:
        failures.append(
            "LOGIC_CONFLICT: criteria 存在 INSUFFICIENT 但 overall=ELIGIBLE（已由 Final Gate 纠正）"
        )
    return failures


# ── Step 4: recommendations ──────────────────────────────────
def generate_recommendations(
    result: EligibilityJudgment, policy_title: str
) -> tuple[list, list, list]:
    missing_materials, risks, next_actions = [], [], []
    for c in result.criteria:
        if c.result == CriterionResult.INSUFFICIENT and c.missing_information:
            missing_materials.append(
                MissingMaterial(material=c.missing_information, reason=c.reason)
            )
        if c.result == CriterionResult.FAIL:
            risks.append(
                RiskItem(
                    risk=f"不满足条件: {c.criterion[:50]}",
                    severity="high",
                    mitigation=f"需补齐: {c.missing_information or c.reason}",
                )
            )
    if result.overall_result == OverallResult.INSUFFICIENT_INFO:
        next_actions.append(
            NextBestAction(
                action="完善企业画像", description="补充缺失信息以获得准确判定", cta="更新画像"
            )
        )
    if result.overall_result == OverallResult.REQUIRES_REVIEW:
        next_actions.append(NextBestAction(action="人工复核", description="逐条核验条件完整性、企业事实来源与当期申报要求。", cta="复核证据"))
    if result.overall_result == OverallResult.ELIGIBLE:
        next_actions.append(
            NextBestAction(
                action="生成申报材料",
                description=f"企业符合 {policy_title} 申报条件，建议启动申报",
                product_code="APPLICATION_PLAN",
                cta="查看申报方案",
            )
        )
    if missing_materials:
        next_actions.append(
            NextBestAction(
                action="生成材料清单",
                description=f"共 {len(missing_materials)} 项材料需要准备",
                cta="查看清单",
            )
        )
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
    start = datetime.now(UTC)
    telemetry: dict = {
        "llm_call_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "tokens_available": False,
        "validation_failure_count": 0,
        "retry_count": 0,
        "retrieval_count": 0,
    }

    # Step 0: Fact normalization（D7）
    facts = normalize_facts(company_profile)

    # Step 1: Extract criteria（D4 窗口 6000）
    criteria_raw = await extract_criteria(policy_content, provider)
    if not criteria_raw:
        return PolicyEvaluationResult(
            overall_result=OverallResult.INSUFFICIENT_INFO,
            matched_policy_id=policy_id,
            matched_policy_title=policy_title,
            summary="政策内容为空或过短，无法提取申报条件。",
            model_metadata={"engine_version": ENGINE_VERSION, "provider": provider},
        )

    # Step 1.5: 结构化 + 拆分（D8）
    criteria_norm = normalize_criteria(criteria_raw)

    # Step 2: LLM 判定 semantic 条件（numeric 条件不再让 LLM 心算）
    judgment, llm_tel = await evaluate_criteria(
        criteria_norm, company_name, company_profile, provider
    )
    telemetry.update(llm_tel)

    # Step 2.5: deterministic 交叉验证（D1）—— 程序优先
    det_results: list[dict] = []
    llm_by_text = {c.criterion: c for c in judgment.criteria}
    merged: list[CriterionEvaluation] = []
    for cn in criteria_norm:
        det = evaluate_deterministic(cn, facts)
        llm_ce = llm_by_text.get(cn["criterion"])
        if det is not None:
            det_results.append({"criterion": cn["criterion"], **det})
            prog = CriterionResult(det["result"])
            audit_note = (
                f"[deterministic] enterprise_value={det['enterprise_value']} "
                f"{det['operator']} threshold={det['threshold']} {det.get('note', '')}"
            )
            if llm_ce is not None and llm_ce.result != prog:
                audit_note += f"｜[交叉验证] LLM原判{llm_ce.result.value}与程序冲突，以程序为准"
                telemetry["validation_failure_count"] += 1
            merged.append(
                CriterionEvaluation(
                    criterion=cn["criterion"],
                    enterprise_fact=(llm_ce.enterprise_fact if llm_ce else "由程序计算"),
                    policy_requirement=cn["policy_quote"],
                    evidence_quote=cn["policy_quote"],
                    evidence_source="政策原文",
                    result=prog,
                    reason=((llm_ce.reason + "｜" if llm_ce else "") + audit_note),
                    missing_information=(llm_ce.missing_information if llm_ce else ""),
                    confidence=0.95 if (llm_ce is None or llm_ce.result == prog) else 0.85,
                )
            )
        elif llm_ce is not None:
            # A model assertion alone is not an auditable hard-condition check.
            # Preserve its proposal as text, but require human verification.
            llm_ce.result = CriterionResult.INSUFFICIENT
            llm_ce.reason += "｜语义条件尚无确定性事实核验，需人工复核"
            llm_ce.missing_information = "请核验企业事实与该政策条件的对应证据"
            llm_ce.confidence = min(llm_ce.confidence, 0.3)
            merged.append(llm_ce)
        else:
            merged.append(
                CriterionEvaluation(
                    criterion=cn["criterion"],
                    enterprise_fact="数据不足",
                    policy_requirement=cn["policy_quote"],
                    evidence_quote=cn["policy_quote"],
                    evidence_source="政策原文",
                    result=CriterionResult.INSUFFICIENT,
                    reason="LLM 未返回该条件的判定",
                    missing_information="需补充相关企业信息",
                    confidence=0.2,
                )
            )
    judgment.criteria = merged

    # Step 3: Evidence Gate（精准化）
    judgment, hallucinations = validate_evidence(judgment, policy_content)

    # Step 3.5: Final Eligibility Gate（D3 程序聚合，V2.2 区分阻断性/软性条件）
    blocking = [_is_blocking(cn["criterion"], cn.get("kind")) for cn in criteria_norm]
    overall_str = final_gate([c.result.value for c in judgment.criteria], blocking)
    if len(policy_content) > 6000 and overall_str == "ELIGIBLE":
        overall_str = "INSUFFICIENT_INFO"
    elif overall_str == "ELIGIBLE":
        # Extraction completeness and fact provenance have not been reviewed.
        # This legacy LLM path cannot issue a final eligibility certificate.
        overall_str = "REQUIRES_REVIEW"
    judgment.overall_result = OverallResult(overall_str)
    judgment.summary = {
        "ELIGIBLE": "已提取条件通过程序核验；仍需人工复核原文条件完整性，不代表主管部门确认。",
        "NOT_ELIGIBLE": "至少一项已核验硬条件不满足。",
        "INSUFFICIENT_INFO": "证据、条件完整性或企业事实不足，需补充资料并人工复核。",
        "REQUIRES_REVIEW": "已提取条件通过程序核验；条件完整性与企业事实来源仍需人工复核。",
    }[overall_str]
    logic_failures = logic_validate(judgment)
    telemetry["validation_failure_count"] += len(logic_failures)

    # Step 4: recommendations
    missing_materials, risks, next_actions = generate_recommendations(judgment, policy_title)

    evidence = [
        EvidenceItem(
            source_title=policy_title,
            publisher="来源机构待核验",
            quote=c.get("policy_quote", "")[:200],
            confidence=0.9,
        )
        for c in criteria_raw[:6]
        if exact_quote_span(policy_content, c.get("policy_quote", "")) is not None
    ]

    end = datetime.now(UTC)
    latency = int((end - start).total_seconds() * 1000)

    hard_failures = [c.criterion for c in judgment.criteria if c.result == CriterionResult.FAIL]
    missing_info = [
        c.missing_information
        for c in judgment.criteria
        if c.result == CriterionResult.INSUFFICIENT and c.missing_information
    ]

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
        summary=judgment.summary
        or f"针对 {policy_title} 的资格判定结果：{judgment.overall_result.value}",
        model_metadata={
            "engine_version": ENGINE_VERSION,
            "prompt_version": PROMPT_VERSION,
            "provider": provider,
            "latency_ms": latency,
            "policy_level": policy_level,
            "hallucinations_blocked": len(hallucinations),
            "criteria_count": len(criteria_raw),
            "deterministic_evaluated": len(det_results),
            "telemetry": telemetry,
            "logic_failures": logic_failures,
        },
    )
