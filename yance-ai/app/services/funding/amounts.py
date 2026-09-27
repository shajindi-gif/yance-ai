"""Deterministic parsing of Chinese funding-amount strings into structured facts.

The policy knowledge base stores amounts as free text (e.g. "最高500万",
"100万-300万元", "按研发投入30%补助，上限200万"). This module converts those
strings into numeric min/max/ratio fields WITHOUT any LLM: anything it cannot
parse with confidence stays NULL (INSUFFICIENT EVIDENCE by design).
"""

import re
from dataclasses import dataclass

# Multipliers for 亿/万 units; plain numbers are treated as 元 and converted to 万.
_UNIT_MULTIPLIERS = {"亿": 10000.0, "万": 1.0}
_MAX_RE = r"(?:最高|不超过|上限(?:为|不超过)?|至多|不高于|封顶(?:为)?|单一项目.{0,6}上限)"
_MIN_RE = r"(?:最低|不低于|下限)"
_RATIO_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[%％]")
_RANGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*([亿万]?)\s*元?\s*(?:[-—~～至到]|\s{1,3})\s*(\d+(?:\.\d+)?)\s*([亿万])\s*元?"
)
_SINGLE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([亿万])\s*元?")


@dataclass(frozen=True)
class FundingAmount:
    amount_min: float | None  # 万元
    amount_max: float | None  # 万元
    ratio: float | None  # %
    parsed: bool  # True when at least one numeric fact was extracted


def _to_wan(value: float, unit: str) -> float:
    if unit == "亿":
        return value * 10000.0
    if unit == "万":
        return value
    # Bare number: assume 元 only when large; small bare numbers are ambiguous.
    return value / 10000.0 if value >= 10000 else value


def _has_unit(text: str) -> bool:
    return bool(re.search(r"\d\s*[亿万]", text)) or bool(re.search(r"\d{5,}", text))


def parse_support_amount(raw: str | None) -> FundingAmount:
    """Parse a support_amount string into structured funding facts.

    Returns parsed=False (all NULLs) when the text carries no confident number.
    """
    if not raw or not raw.strip():
        return FundingAmount(None, None, None, False)

    text = raw.strip()
    ratio = None
    ratio_match = _RATIO_RE.search(text)
    if ratio_match:
        ratio = float(ratio_match.group(1))

    amount_min = None
    amount_max = None
    parsed = False

    range_match = _RANGE_RE.search(text)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(3))
        low_unit = range_match.group(2) or ""
        high_unit = range_match.group(4) or ""
        amount_min = _to_wan(low, low_unit)
        amount_max = _to_wan(high, high_unit)
        if amount_min > amount_max:
            amount_min, amount_max = amount_max, amount_min
        parsed = True
    else:
        max_marker = re.search(_MAX_RE, text)
        min_marker = re.search(_MIN_RE, text)
        single = _SINGLE_RE.search(text) if _has_unit(text) else None
        if single and float(single.group(1)) >= 10000 and not _has_unit(text):
            single = None  # ambiguous bare number without unit
        if single:
            value = _to_wan(float(single.group(1)), single.group(2))
            parsed = True
            if max_marker:
                amount_max = value
            elif min_marker:
                amount_min = value
            else:
                amount_min = value
                amount_max = value

    return FundingAmount(
        round(amount_min, 2) if amount_min is not None else None,
        round(amount_max, 2) if amount_max is not None else None,
        ratio,
        parsed,
    )


def infer_funding_type(raw: str | None, support_type: str | None = None) -> str | None:
    """Classify funding_type from official wording. NULL when ambiguous."""
    text = f"{support_type or ''} {raw or ''}"
    rules = (
        ("tax_incentive", ("税收", "减免税", "免税", "加计扣除", "退税")),
        ("loan_discount", ("贴息", "贷款", "担保费")),
        ("voucher", ("券", "算力券", "创新券", "服务券")),
        ("talent", ("人才", "领军", "拔尖")),
        ("competition", ("大赛", "赛事", "赛会", "比选赛")),
        ("equity", ("基金", "股权投资", "直投")),
        ("grant", ("补助", "资助", "补贴", "奖励", "支持资金", "专项资金", "资助资金")),
    )
    for code, markers in rules:
        if any(marker in text for marker in markers):
            return code
    return None
