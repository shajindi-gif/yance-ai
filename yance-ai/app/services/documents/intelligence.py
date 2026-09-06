import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.config import settings
from app.services.documents.parsers import ParsedDocument

EXTRACTION_VERSION = "company-intelligence-v1"


@dataclass(frozen=True)
class FactCandidate:
    field_key: str
    value: Any
    confidence: float
    evidence_excerpt: str
    source_locator: dict[str, Any]
    candidate_hash: str


def _locator(parsed: ParsedDocument, start: int, end: int) -> dict[str, Any]:
    locator: dict[str, Any] = {"character_start": start, "character_end": end}
    for span in parsed.spans:
        if start < span.end and end > span.start:
            locator.update(span.locator)
            break
    return locator


def _candidate(
    parsed: ParsedDocument,
    field_key: str,
    value: Any,
    confidence: float,
    match: re.Match[str],
) -> FactCandidate:
    excerpt_start = max(0, match.start() - 80)
    excerpt_end = min(len(parsed.text), match.end() + 120)
    excerpt = parsed.text[excerpt_start:excerpt_end].strip()
    canonical = json.dumps(
        {"field_key": field_key, "value": value, "excerpt": excerpt},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return FactCandidate(
        field_key=field_key,
        value=value,
        confidence=confidence,
        evidence_excerpt=excerpt,
        source_locator=_locator(parsed, match.start(), match.end()),
        candidate_hash=hashlib.sha256(canonical.encode()).hexdigest(),
    )


def _split_list(value: str) -> list[str]:
    return [item.strip(" 、,，;；") for item in re.split(r"[、,，;；]", value) if item.strip()][:100]


def _money(value: str, unit: str) -> float:
    number = float(value.replace(",", ""))
    return number * {"亿元": 100_000_000, "万元": 10_000, "元": 1}[unit]


def extract_company_intelligence(parsed: ParsedDocument) -> list[FactCandidate]:
    """Conservative extraction: labelled or strongly formatted facts only."""

    patterns: list[tuple[str, re.Pattern[str], Any, float]] = [
        (
            "industry",
            re.compile(r"(?:所属行业|行业)\s*[:：]\s*([^\n\t]{2,80})"),
            lambda m: m.group(1).strip(),
            0.92,
        ),
        (
            "registered_address",
            re.compile(r"(?:注册地址|注册住所)\s*[:：]\s*([^\n\t]{4,300})"),
            lambda m: m.group(1).strip(),
            0.96,
        ),
        (
            "founded_date",
            re.compile(r"(?:成立日期|成立时间)\s*[:：]\s*(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?"),
            lambda m: date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat(),
            0.96,
        ),
        (
            "employee_count",
            re.compile(r"(?:员工人数|职工人数|从业人员)\s*[:：为]?\s*(\d{1,8})\s*人"),
            lambda m: int(m.group(1)),
            0.94,
        ),
        (
            "annual_revenue",
            re.compile(r"(?:年度营业收入|年营业收入|营业收入|年度营收)\s*[:：为]?\s*([\d,.]+)\s*(亿元|万元|元)"),
            lambda m: _money(m.group(1), m.group(2)),
            0.93,
        ),
        (
            "rd_expense_ratio",
            re.compile(r"(?:研发费用|研发投入)[^\n%]{0,60}?(?<![\d.])(\d{1,3}(?:\.\d+)?)\s*%"),
            lambda m: float(m.group(1)),
            0.90,
        ),
        (
            "funding_stage",
            re.compile(r"融资阶段\s*[:：]\s*([^\n\t]{1,40})"),
            lambda m: m.group(1).strip(),
            0.90,
        ),
        (
            "core_products",
            re.compile(r"(?:核心产品|主要产品)\s*[:：]\s*([^\n]{2,500})"),
            lambda m: _split_list(m.group(1)),
            0.88,
        ),
        (
            "intellectual_property",
            re.compile(r"(?:知识产权|专利及软著)\s*[:：]\s*([^\n]{2,500})"),
            lambda m: _split_list(m.group(1)),
            0.88,
        ),
        (
            "projects",
            re.compile(r"(?:在研项目|重点项目|项目情况)\s*[:：]\s*([^\n]{2,500})"),
            lambda m: _split_list(m.group(1)),
            0.86,
        ),
        (
            "current_needs",
            re.compile(r"(?:当前需求|政策需求|申报需求)\s*[:：]\s*([^\n]{2,500})"),
            lambda m: _split_list(m.group(1)),
            0.88,
        ),
    ]
    results: list[FactCandidate] = []
    seen_fields: set[str] = set()
    for field_key, pattern, transform, confidence in patterns:
        match = pattern.search(parsed.text)
        if not match or field_key in seen_fields:
            continue
        try:
            value = transform(match)
        except (TypeError, ValueError):
            continue
        if value in (None, "", []):
            continue
        results.append(_candidate(parsed, field_key, value, confidence, match))
        seen_fields.add(field_key)

    status_patterns = (
        ("high_tech_status", r"高新技术企业(?:资质|认定)?\s*[:：]\s*([^\n\t]{2,40})"),
        ("tech_sme_status", r"科技型中小企业(?:资质|认定)?\s*[:：]\s*([^\n\t]{2,40})"),
        ("specialized_sme_status", r"专精特新(?:企业)?(?:资质|认定)?\s*[:：]\s*([^\n\t]{2,40})"),
    )
    for field_key, source_pattern in status_patterns:
        match = re.search(source_pattern, parsed.text)
        if match:
            results.append(_candidate(parsed, field_key, match.group(1).strip(), 0.90, match))
    return results


def chunk_document(parsed: ParsedDocument) -> list[dict[str, Any]]:
    text = parsed.text
    size = settings.document_chunk_size_chars
    overlap = min(settings.document_chunk_overlap_chars, max(size - 1, 0))
    chunks: list[dict[str, Any]] = []
    start = 0
    sequence = 0
    while start < len(text):
        hard_end = min(start + size, len(text))
        end = hard_end
        if hard_end < len(text):
            boundary = max(text.rfind("\n", start, hard_end), text.rfind("。", start, hard_end))
            if boundary > start + size // 2:
                end = boundary + 1
        content = text[start:end].strip()
        if content:
            locator = _locator(parsed, start, end)
            chunks.append(
                {
                    "sequence": sequence,
                    "content": content,
                    "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "character_start": start,
                    "character_end": end,
                    "token_estimate": max(1, len(content) // 2),
                    "locator_json": locator,
                }
            )
            sequence += 1
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks
