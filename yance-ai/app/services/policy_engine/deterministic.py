"""Policy Evaluation Engine V2.1 — Deterministic Evaluator & Fact Normalization
系统性修复（对齐 benchmark/V21_AUDIT.md D1/D7/D8）：
- normalize_facts(): Enterprise Fact Normalization —— 画像字段归一为标准事实表
- normalize_criteria(): 政策条件结构化（field/operator/value），组合条件拆分
- evaluate_deterministic(): 数字/比例/年限/布尔条件由 Python 计算，禁止 LLM 心算
- 红线：不做 case_id 级特判；只实现通用 evaluator。
"""
from __future__ import annotations
import re
from datetime import date
from typing import Any, Optional

# ────────────────────────── Fact Normalization ──────────────────────────

_FIELD_ALIASES: dict[str, list[str]] = {
    "founded_date": ["registration_date", "注册日期", "成立日期", "founded", "成立时间", "founding_date"],
    "employee_count": ["employees_total", "员工总数", "职工总数", "employees", "员工数", "total_staff"],
    "tech_staff": ["tech_staff", "科技人员", "tech_staff_rd_staff", "rd_staff", "研发人员"],
    "rd_staff_ratio": ["rd_staff_ratio", "研发人员占比", "科技人员占比"],
    "rd_expense_3y": ["rd_expense_recent_3y_total_wan", "近三年研发费用", "rd_expense_3y_wan"],
    "revenue_3y": ["revenue_recent_3y_total_wan", "近三年销售收入", "近三年营业收入"],
    "revenue_last_year": ["revenue_last_year_wan", "上年度营业收入", "上年度销售收入", "去年收入"],
    "rd_expense_last_year": ["rd_expense_last_year_wan", "上年度研发费用"],
    "rd_ratio_3y": ["rd_expense_ratio_3y"],
    "rd_ratio_last_year": ["rd_expense_ratio_last_year", "研发费用占比"],
    "hitech_product_revenue_ratio": ["hitech_product_revenue_ratio", "高新收入占比", "高新技术产品收入占比"],
    "domestic_rd_ratio": ["domestic_rd_ratio", "境内研发占比"],
    "has_ip": ["core_ip", "知识产权", "has_ip"],
    "ip_count": ["ip_count", "专利数量", "知识产权数量"],
    "hognqi_status": ["hognqi_status", "高企资质", "高新技术企业资质", "has_high_tech_cert"],
    "market_segment_years": ["market_segment_years", "细分市场年限", "从事特定细分市场时间"],
    "main_revenue_last_year": ["main_revenue_last_year_wan", "上年度主营业务收入"],
    "listed": ["listed", "是否上市", "is_listed"],
    "equity_financing_2y": ["equity_financing_recent_2y_wan", "近两年股权融资"],
    "equity_financing_3y": ["equity_financing_3y_wan", "近三年股权融资"],
    "revenue_cagr_3y": ["revenue_cagr_3y", "复合增长率", "前三年主营业务收入复合增长率"],
    "net_profit_margin": ["net_profit_margin_last_year", "净利润率"],
    "industry": ["industry", "行业"],
    "city": ["city", "城市"],
    "province": ["province", "省份"],
    "safety_violations": ["safety_env_violations_last_1y", "安全环境违法"],
}

_NUM = r"(-?\d+(?:\.\d+)?)"


def _parse_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    m = re.search(_NUM, s.replace(",", "").replace("，", ""))
    if not m:
        return None
    n = float(m.group(1))
    # 单位归一：万元 → 元数量级保持“万”为基准（本引擎统一以“万”为单位）
    if re.search(r"亿", s) and "亿" not in str(v)[: m.start() + 1]:
        pass
    if "亿" in s:
        n *= 10000.0  # 亿 → 万
    return n


def _parse_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    s = str(v)
    m = re.search(r"(\d{4})[-/年.](\d{1,2})?[-/月.]?(\d{1,2})?", s)
    if not m:
        return None
    y = int(m.group(1))
    mo = int(m.group(2) or 1)
    d = int(m.group(3) or 1)
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _to_ratio(v: Any) -> Optional[float]:
    """归一为小数比例。'12%' → 0.12；0.124 → 0.124；'12.4%'→0.124"""
    if v is None:
        return None
    s = str(v)
    m = re.search(_NUM, s)
    if not m:
        return None
    n = float(m.group(1))
    if "%" in s or "％" in s:
        return n / 100.0
    if n > 1.5:  # 12.4 这样的裸数字按百分数理解（占比字段惯例）
        return n / 100.0
    return n


def _parse_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    s = str(v).strip()
    if re.search(r"有效期内|已获得|是|有|true|yes|已认定|已取得", s):
        return True
    if re.search(r"未提供|null|none|缺失|unknown", s, re.I):
        return None
    if re.search(r"无|否|没有|false|no|未获得", s):
        return False
    return None


def normalize_facts(profile: dict) -> dict:
    """企业画像 → 标准事实表。只归一，不猜测：找不到的字段值为 None。"""
    facts: dict[str, Any] = {}
    lower = {str(k).lower(): v for k, v in profile.items()}

    def pick(std: str):
        # 始终把规范键本身加入候选，避免「规范键漏写进 alias 列表」导致字段丢失
        aliases = list(_FIELD_ALIASES.get(std, [])) + [std]
        for alias in aliases:
            if alias in profile:
                return profile[alias]
            if alias.lower() in lower:
                return lower[alias.lower()]
        return None

    for std in _FIELD_ALIASES:
        raw = pick(std)
        if raw is None:
            facts[std] = None
            continue
        if std in ("founded_date",):
            facts[std] = _parse_date(raw)
        elif std in ("rd_staff_ratio", "rd_ratio_last_year", "rd_ratio_3y", "hitech_product_revenue_ratio",
                     "domestic_rd_ratio", "revenue_cagr_3y", "net_profit_margin"):
            facts[std] = _to_ratio(raw)
        elif std in ("has_ip", "hognqi_status", "listed"):
            facts[std] = _parse_bool(raw)
        elif std in ("safety_violations",):
            s = str(raw)
            facts[std] = None if re.search(r"未提供|null", s, re.I) else not bool(re.search(r"无|未发生|没有", s))
        elif std in ("employee_count", "tech_staff", "ip_count"):
            facts[std] = _parse_number(raw)
        elif std in ("market_segment_years",):
            facts[std] = _parse_number(raw)
        else:  # 金额类统一“万”
            facts[std] = _parse_number(raw)

    # 派生事实（仅当分量存在时计算，绝不猜测）
    if facts.get("tech_staff") is not None and facts.get("employee_count"):
        facts["tech_staff_ratio"] = facts["tech_staff"] / facts["employee_count"]
    else:
        facts["tech_staff_ratio"] = facts.get("rd_staff_ratio")

    if facts.get("rd_expense_3y") is not None and facts.get("revenue_3y"):
        facts["rd_ratio_3y"] = facts["rd_expense_3y"] / facts["revenue_3y"]

    if facts.get("rd_expense_last_year") is not None and facts.get("revenue_last_year"):
        facts["rd_ratio_last_year"] = facts["rd_expense_last_year"] / facts["revenue_last_year"]

    # 公司规模分档辅助：最近一年收入（万）
    facts["revenue_last_year_wan"] = facts.get("revenue_last_year")
    return facts


# ────────────────────────── Criteria Normalization ──────────────────────────

_FIELD_PATTERNS: list[tuple[str, list[str]]] = [
    # (标准字段, 触发关键词)
    # 注意顺序：越具体的字段越靠前（_detect_field 取首个匹配）。
    #   tech_staff_ratio 的「科技人员占…职工总数」同时含 employee_count 的「职工总数」，
    #   故必须排在 employee_count 之前，否则高企研发人员占比门槛会被误判为职工总数→错判 PASS。
    ("tech_staff_ratio", ["科技人员占比", "科技人员.*比例", "研发人员.*比例", "科技人员占", "研发人员占", "科技人员占.*职工总数"]),
    ("rd_ratio_3y", ["近.{0,2}3?.{0,2}会计年度.{0,10}研究开发费用", "近三个会计年度.{0,12}研发", "研发费用总额占.{0,8}收入"]),
    ("rd_ratio_last_year", ["上年度研发费用", "研发费用总额不低于"]),
    ("hitech_product_revenue_ratio", ["高新技术产品.{0,6}收入占", "高新收入占比"]),
    ("domestic_rd_ratio", ["境内.{0,10}研究开发费用", "境内研发"]),
    ("employee_count", ["职工总数", "从业人员", "员工总数", "员工人数", "职工人数"]),
    ("revenue_last_year", ["上年度.{0,8}营业收入总额", "上年度.{0,8}销售收入", "上年度主营业务收入", "营业收入总额在", "销售收入在", "销售收入不超过", "销售收入总额", "营业收入总额"]),
    ("total_assets", ["资产总额", "总资产"]),
    ("founded_years", ["注册成立", "成立.{0,4}年", "注册登记满"]),
    ("has_ip", ["知识产权", "专利", "软著", "软件著作权"]),
    ("hognqi_status", ["高新技术企业资质", "高新技术企业认定", "已获得高新技术企业"]),
    ("market_segment_years", ["从事特定细分市场时间", "细分市场.{0,6}年"]),
    ("listed", ["非上市", "未上市", "上市企业"]),
    ("equity_financing_2y", ["近.?2.?.{0,6}股权融资", "近两年新增股权融资"]),
    ("equity_financing_3y", ["近.?3.?.{0,6}股权融资", "前三年.{0,6}股权融资"]),
    ("revenue_cagr_3y", ["复合增长率"]),
    ("net_profit_margin", ["净利润率"]),
    ("safety_violations", ["安全.{0,4}质量事故|环境违法"]),
]

_OPS: list[tuple[str, str]] = [
    # 长词/否定形式优先，避免子串污染（"不超过"含"超过"，"不低于"含"低于"）
    ("不低于", ">="), ("不少于", ">="), ("不高于", "<="), ("不超过", "<="), ("未满", "<"),
    ("达到", ">="), ("以上", ">="), ("超过", ">"), ("至少", ">="),
    ("以下", "<="), ("以内", "<="), ("低于", "<"), ("之间", "between"),
]

_UNIT_PAT = r"(万元|亿元|%|人|年|项|件)"


def _detect_field(cond: str) -> Optional[str]:
    for field, pats in _FIELD_PATTERNS:
        for p in pats:
            if re.search(p, cond):
                return field
    return None


def _detect_op(cond: str) -> Optional[str]:
    for word, op in _OPS:
        if word in cond:
            return op
    return None


def _detect_value(cond: str, field: str) -> Optional[tuple[float, Optional[str]]]:
    """返回 (数值, 单位)。金额类返回“万”口径。"""
    m = re.findall(r"(\d[\d,\.]*)\s*(万元|亿元|%|％|人|年|项|件)", cond)
    if not m:
        m2 = re.search(r"(\d[\d,\.]*)", cond)
        return (float(m2.group(1).replace(",", "")), None) if m2 else None
    num_s, unit = m[-1]
    n = float(num_s.replace(",", ""))
    if unit == "亿元":
        n *= 10000.0
        unit = "万元"
    if unit in ("%", "％") and field in ("rd_ratio_3y", "rd_ratio_last_year", "hitech_product_revenue_ratio",
                                        "domestic_rd_ratio", "tech_staff_ratio", "revenue_cagr_3y",
                                        "net_profit_margin"):
        return (n / 100.0, "ratio")
    return (n, unit)


def _split_composite(cond: str) -> list[str]:
    """组合条件拆分：'A不超过500人、B不超过2亿、C不超过2亿' → 三条。
    仅当拆出的片段各自包含 数字+单位 时才独立成条，否则保留原句。"""
    parts = re.split(r"[、；;]", cond)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        return [cond]
    numbered = [p for p in parts if re.search(r"\d[\d,\.]*\s*(万元|亿元|%|％|人|年|项|件)", p)]
    if len(numbered) >= 2:
        # 把主语补进片段：若片段过短（<8字）保留原句兜底
        return parts if all(len(p) >= 6 for p in parts) else [cond]
    return [cond]


def normalize_criteria(criteria: list[dict]) -> list[dict]:
    """自然语言条件 → 结构化。未识别字段的条件标记 kind='semantic'，交 LLM 判定。"""
    out = []
    for c in criteria:
        cond = c.get("criterion", "") if isinstance(c, dict) else str(c)
        quote = c.get("policy_quote", cond) if isinstance(c, dict) else cond
        for piece in _split_composite(cond):
            item = {
                "criterion": piece,
                "policy_quote": quote,
                "field": None, "operator": None, "value": None, "unit": None,
                "kind": "semantic",
            }
            field = _detect_field(piece)
            op = _detect_op(piece)
            if field and op:
                val = _detect_value(piece, field)
                if val is not None:
                    v, unit = val
                    item.update({"field": field, "operator": op, "value": v, "unit": unit, "kind": "numeric"})
            out.append(item)
    return out


# ────────────────────────── Deterministic Evaluation ──────────────────────────

def _cmp(value: float, op: str, threshold: float, threshold2: Optional[float] = None) -> bool:
    if op == ">=":
        return value >= threshold
    if op == ">":
        return value > threshold
    if op == "<=":
        return value <= threshold
    if op == "<":
        return value < threshold
    if op == "=":
        return abs(value - threshold) < 1e-9
    if op == "between" and threshold2 is not None:
        return threshold <= value <= threshold2
    return False


def _hnte_rd_ratio_threshold(revenue_wan: Optional[float]) -> Optional[tuple[float, str]]:
    """高企研发费用占比分档：收入<5000万→5%；5000万-2亿→4%；>2亿→3%（32号文第十一条(五)）。"""
    if revenue_wan is None:
        return None
    if revenue_wan < 5000:
        return (0.05, "<5000万档")
    if revenue_wan <= 20000:
        return (0.04, "5000万-2亿档")
    return (0.03, ">2亿档")


def evaluate_deterministic(criterion: dict, facts: dict) -> Optional[dict]:
    """对 numeric 类条件做程序判定。返回 None 表示无法程序判定（交 LLM）。
    结果含审计五元组：enterprise_value / operator / threshold / calculated_value / result。
    """
    field, op, val = criterion.get("field"), criterion.get("operator"), criterion.get("value")
    if criterion.get("kind") != "numeric" or field is None:
        return None

    def res(v, op_, th, note=""):
        return {
            "result": "PASS" if _cmp(v, op_, th) else "FAIL",
            "enterprise_value": v, "operator": op_, "threshold": th,
            "calculated_value": v, "note": note,
        }

    # —— 高企研发占比分档（需要收入定档） ——
    if field in ("rd_ratio_3y",) and criterion.get("unit") == "ratio" and op == ">=":
        ratio = facts.get("rd_ratio_3y")
        rev = facts.get("revenue_last_year_wan") or facts.get("revenue_last_year")
        if ratio is None:
            return None
        th = _hnte_rd_ratio_threshold(rev)
        if th is None:
            return None  # 收入缺失 → 交 LLM 走 INSUFFICIENT（不猜测档位）
        r = res(ratio, ">=", th[0], f"高企分档：{th[1]}（最近1年收入{rev}万）")
        return r

    if field in ("rd_ratio_last_year",) and criterion.get("unit") == "ratio" and op == ">=":
        ratio = facts.get("rd_ratio_last_year")
        if ratio is None:
            return None
        return res(ratio, ">=", val)

    if field == "tech_staff_ratio" and criterion.get("unit") in ("ratio", None):
        ratio = facts.get("tech_staff_ratio")
        if ratio is None:
            return None
        return res(ratio, ">=" if op == ">=" else op, val)

    if field == "hitech_product_revenue_ratio":
        ratio = facts.get("hitech_product_revenue_ratio")
        if ratio is None:
            return None
        return res(ratio, op, val)

    if field == "domestic_rd_ratio":
        ratio = facts.get("domestic_rd_ratio")
        if ratio is None:
            return None
        return res(ratio, op, val)

    if field == "employee_count" and op in ("<=", ">=", "<", ">"):
        v = facts.get("employee_count")
        if v is None:
            return None
        return res(v, op, val)

    if field == "revenue_last_year" and op in ("<=", ">=", "<", ">", "between"):
        v = facts.get("revenue_last_year")
        if v is None:
            return None
        # “1000万元以上”含本数口径已在 Gold 中披露；这里按 >= 处理
        return res(v, op, val)

    if field == "founded_years" and op == ">=":
        fd = facts.get("founded_date")
        if fd is None:
            return None
        years = (date.today() - fd).days / 365.25
        return res(round(years, 2), ">=", val, f"成立至今 {years:.2f} 年（截至 {date.today()}）")

    if field == "market_segment_years" and op == ">=":
        v = facts.get("market_segment_years")
        if v is None:
            return None
        return res(v, ">=", val)

    if field == "revenue_cagr_3y" and criterion.get("unit") == "ratio":
        v = facts.get("revenue_cagr_3y")
        if v is None:
            return None
        return res(v, op, val)

    if field == "net_profit_margin" and criterion.get("unit") == "ratio":
        v = facts.get("net_profit_margin")
        if v is None:
            return None
        return res(v, op, val)

    return None


# ────────────────────────── Final Eligibility Gate ──────────────────────────

def final_gate(criteria_results: list[str], blocking: Optional[list[bool]] = None) -> str:
    """程序化聚合（对齐 V21_AUDIT D3）：LLM 无权绕过。
    V2.2：仅『阻断性』条件参与否决。
      - 任一阻断性 FAIL → NOT_ELIGIBLE
      - 任一阻断性 INSUFFICIENT → INSUFFICIENT_INFO
      - 仅有软性（advisory）条件 INSUFFICIENT，而所有硬门槛 PASS → ELIGIBLE
    空 criteria → INSUFFICIENT_INFO（保守）。
    """
    if not criteria_results:
        return "INSUFFICIENT_INFO"
    if blocking is None:
        blocking = [True] * len(criteria_results)
    if any(r == "FAIL" and b for r, b in zip(criteria_results, blocking)):
        return "NOT_ELIGIBLE"
    if any(r == "INSUFFICIENT" and b for r, b in zip(criteria_results, blocking)):
        return "INSUFFICIENT_INFO"
    return "ELIGIBLE"


# —— 软性/主观条件识别（V2.2）：这类条件不阻断资格，仅作提示 ——
_SOFT_PAT = re.compile(
    r"评价得分|得分|创新能力评价|成长性指标|专业化指标|创新能力指标|荣誉|奖励|大赛|排名"
    r"|应达到相应要求|综合评分|加分")


def _is_blocking(text: str, kind: Optional[str] = None) -> bool:
    """判断某条件是否『阻断性硬门槛』。
    - 主观/复合评分/荣誉奖励类 → 软性（不阻断）
    - 安全事故、环境违法、社会信用条件始终按硬门槛处理
    - 含须/必须/应当/不得/应 等强制语 → 阻断
    - 数字硬门槛（kind=numeric）→ 阻断
    - 其它语义条件 → 默认阻断（保守）
    """
    t = text or ""
    if _SOFT_PAT.search(t):
        return False
    if re.search(r"须|必须|应当|不得|应", t):
        return True
    if kind == "numeric":
        return True
    return True
