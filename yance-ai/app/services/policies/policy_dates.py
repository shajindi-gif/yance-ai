"""Extract explicit calendar dates from policy text. Never invent missing windows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

_YMD = re.compile(
    r"(?P<y>20\d{2})\s*[年./-]\s*(?P<m>\d{1,2})\s*[月./-]\s*(?P<d>\d{1,2})\s*日?"
)

_EFFECTIVE_HINTS = ("起施行", "起实施", "之日起施行", "之日起实施", "发布之日起施行", "自发布之日起")
_EXPIRES_HINTS = ("有效期至", "有效期截止", "有效期截至", "有效期到", "废止日期", "失效日期")
_DEADLINE_HINTS = ("申报截止", "申请截止", "截止日期", "截止时间", "报名截止", "受理截止", "提交截止")


@dataclass(frozen=True)
class ExtractedDates:
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    deadline: datetime | None = None
    evidence: dict[str, str] | None = None


def _parse_ymd(year: str, month: str, day: str) -> datetime | None:
    try:
        value = date(int(year), int(month), int(day))
    except ValueError:
        return None
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _date_near_hint(
    text: str,
    hint_index: int,
    hint_len: int,
    *,
    prefer: str,
) -> tuple[datetime | None, str | None]:
    """prefer: 'before' for 自…起施行, 'after' for 有效期至/截止."""

    if prefer == "after":
        region = text[hint_index : min(len(text), hint_index + hint_len + 48)]
        match = _YMD.search(region)
    else:
        region = text[max(0, hint_index - 48) : hint_index + hint_len]
        match = None
        for item in _YMD.finditer(region):
            match = item
    if match is None:
        return None, None
    parsed = _parse_ymd(match.group("y"), match.group("m"), match.group("d"))
    snippet = region[max(0, match.start() - 2) : match.end() + 2].strip()
    return parsed, snippet


def extract_dates_from_text(content: str) -> ExtractedDates:
    """Pull only dates that sit next to explicit effective/expiry/deadline wording."""

    if not content:
        return ExtractedDates(evidence={})
    evidence: dict[str, str] = {}
    effective = expires = deadline = None

    for hint in _EFFECTIVE_HINTS:
        index = content.find(hint)
        if index < 0:
            continue
        value, snippet = _date_near_hint(content, index, len(hint), prefer="before")
        if value:
            effective = value
            evidence["effective_at"] = snippet or hint
            break

    for hint in _EXPIRES_HINTS:
        index = content.find(hint)
        if index < 0:
            continue
        value, snippet = _date_near_hint(content, index, len(hint), prefer="after")
        if value:
            expires = value
            evidence["expires_at"] = snippet or hint
            break

    for hint in _DEADLINE_HINTS:
        index = content.find(hint)
        if index < 0:
            continue
        value, snippet = _date_near_hint(content, index, len(hint), prefer="after")
        if value:
            deadline = value
            evidence["deadline"] = snippet or hint
            break

    # Refuse impossible windows rather than write them into sellable metadata.
    if effective and expires and expires < effective:
        evidence.pop("expires_at", None)
        expires = None
    return ExtractedDates(
        effective_at=effective,
        expires_at=expires,
        deadline=deadline,
        evidence=evidence,
    )


def merge_dates_for_policy(
    *,
    policy: Any,
    version: Any | None,
    content: str | None,
) -> dict[str, Any]:
    """Propose field updates from version columns then explicit text spans.

    Existing non-null policy fields win. Empty stays empty when nothing explicit.
    """

    updates: dict[str, Any] = {}
    evidence: dict[str, str] = {}

    if version is not None:
        if getattr(policy, "effective_at", None) is None and getattr(version, "effective_date", None):
            updates["effective_at"] = version.effective_date
            evidence["effective_at"] = "policy_version.effective_date"
        if getattr(policy, "expires_at", None) is None and getattr(version, "expiry_date", None):
            updates["expires_at"] = version.expiry_date
            evidence["expires_at"] = "policy_version.expiry_date"
        if getattr(policy, "deadline", None) is None and getattr(
            version, "application_deadline", None
        ):
            updates["deadline"] = version.application_deadline
            evidence["deadline"] = "policy_version.application_deadline"

    extracted = extract_dates_from_text(content or "")
    if getattr(policy, "effective_at", None) is None and "effective_at" not in updates and extracted.effective_at:
        updates["effective_at"] = extracted.effective_at
        evidence["effective_at"] = (extracted.evidence or {}).get("effective_at", "text")
    if getattr(policy, "expires_at", None) is None and "expires_at" not in updates and extracted.expires_at:
        updates["expires_at"] = extracted.expires_at
        evidence["expires_at"] = (extracted.evidence or {}).get("expires_at", "text")
    if getattr(policy, "deadline", None) is None and "deadline" not in updates and extracted.deadline:
        updates["deadline"] = extracted.deadline
        evidence["deadline"] = (extracted.evidence or {}).get("deadline", "text")

    effective = updates.get("effective_at") or getattr(policy, "effective_at", None)
    expires = updates.get("expires_at") or getattr(policy, "expires_at", None)
    if effective and expires and expires < effective:
        updates.pop("expires_at", None)
        evidence.pop("expires_at", None)

    return {"updates": updates, "evidence": evidence}
