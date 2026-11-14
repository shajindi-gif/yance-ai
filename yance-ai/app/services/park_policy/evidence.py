"""Evidence graph: policy version ↔ application batch ↔ attachment, plus staleness.

Two state machines that are routinely conflated and must not be:

* **Policy validity** — is the policy document itself still in force
  (in_force / superseded / withdrawn / expired / unknown)?
* **Application window** — is there an open call right now
  (upcoming / open / closed / suspended / unknown)?

A closed window does not mean the policy is abolished, and a 404 on a source URL
does not mean the policy was repealed.  Repeal requires an official document that
says so; a fetch failure only marks ``source_anomaly``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

POLICY_VALIDITY = ("in_force", "superseded", "withdrawn", "expired", "unknown")
WINDOW_STATE = ("upcoming", "open", "closed", "suspended", "unknown")
SOURCE_HEALTH = ("healthy", "source_anomaly", "attachment_missing", "parse_failed", "unverified")

# Documents that may change an earlier conclusion without replacing the policy.
AMENDING_DOC_TYPES = ("correction", "extension", "repeal", "interpretation", "implementation_rule")


class StalenessReason(StrEnum):
    POLICY_VERSION_CHANGED = "policy_version_changed"
    FACT_CHANGED = "fact_changed"
    FACT_CONFLICTED = "fact_conflicted"
    WINDOW_CHANGED = "window_changed"
    POLICY_WITHDRAWN = "policy_withdrawn"
    SOURCE_ANOMALY = "source_anomaly"


@dataclass(frozen=True)
class PolicyEvidenceState:
    policy_id: str
    policy_version_id: str
    validity: str
    version_hash: str
    effective_from: date | None = None
    effective_to: date | None = None
    published_at: date | None = None
    source_health: str = "unverified"
    superseded_by: str | None = None
    amending_docs: tuple[str, ...] = ()
    note: str | None = None

    @property
    def usable_as_basis(self) -> bool:
        return self.validity in {"in_force", "unknown"} and self.source_health == "healthy"


@dataclass(frozen=True)
class WindowState:
    window_id: str
    policy_id: str
    fiscal_year: int | None
    batch_label: str | None
    opens_at: date | None
    closes_at: date | None
    state: str
    deadline_source: str | None = None
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "policy_id": self.policy_id,
            "fiscal_year": self.fiscal_year,
            "batch_label": self.batch_label,
            "opens_at": self.opens_at.isoformat() if self.opens_at else None,
            "closes_at": self.closes_at.isoformat() if self.closes_at else None,
            "state": self.state,
            "deadline_source": self.deadline_source,
            "note": self.note,
        }


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def compute_window_state(
    *,
    opens_at: Any,
    closes_at: Any,
    today: date | None = None,
    suspended: bool = False,
) -> str:
    """Derive the window state from dates only.

    ``unknown`` is returned when the close date is missing — never ``open``.
    Treating an unknown deadline as open is how a product tells a company to
    apply for something that ended last year.
    """
    today = today or date.today()
    if suspended:
        return "suspended"
    start = _as_date(opens_at)
    end = _as_date(closes_at)
    if start is None and end is None:
        return "unknown"
    if start and today < start:
        return "upcoming"
    if end is None:
        return "unknown"
    if today > end:
        return "closed"
    return "open"


def build_window(
    row: Mapping[str, Any],
    *,
    today: date | None = None,
) -> WindowState:
    state = compute_window_state(
        opens_at=row.get("opens_at"),
        closes_at=row.get("closes_at"),
        today=today,
        suspended=bool(row.get("suspended")),
    )
    if row.get("state_override") in WINDOW_STATE:
        state = str(row["state_override"])
    return WindowState(
        window_id=str(row.get("window_id") or "unknown"),
        policy_id=str(row.get("policy_id") or "unknown"),
        fiscal_year=row.get("fiscal_year"),
        batch_label=row.get("batch_label"),
        opens_at=_as_date(row.get("opens_at")),
        closes_at=_as_date(row.get("closes_at")),
        state=state,
        deadline_source=row.get("deadline_source"),
        note=row.get("note"),
    )


def group_windows_by_batch(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, int | None, str], list[WindowState]]:
    """Batches must stay separate: 2025 and 2026 calls are different objects."""
    grouped: dict[tuple[str, int | None, str], list[WindowState]] = {}
    for row in rows:
        window = build_window(row)
        key = (window.policy_id, window.fiscal_year, window.batch_label or "")
        grouped.setdefault(key, []).append(window)
    return grouped


def content_hash(payload: bytes | str) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_validity(
    *,
    versions: Sequence[Mapping[str, Any]],
    latest_version_id: str | None = None,
    today: date | None = None,
    repeal_document_present: bool = False,
    source_health: str = "healthy",
) -> PolicyEvidenceState:
    """Pick the governing version and its validity without overwriting history.

    Rules:
      * an explicit repeal document wins over everything;
      * an explicit effective_to in the past means expired;
      * a version is superseded only when a newer version exists, and the older
        row is kept (never deleted or mutated);
      * a source fetch failure never changes validity — it only flags health.
    """
    if not versions:
        raise ValueError("versions 不能为空")

    ordered = sorted(
        versions,
        key=lambda row: (
            _as_date(row.get("effective_from")) or _as_date(row.get("published_at")) or date.min,
            str(row.get("version_id") or ""),
        ),
    )
    latest = ordered[-1]
    latest_id = latest_version_id or str(latest.get("version_id") or "unknown")
    effective_to = _as_date(latest.get("effective_to"))
    today = today or date.today()

    if repeal_document_present:
        validity = "withdrawn"
        note = "存在官方废止文件，按已废止处理"
    elif latest.get("withdrawn"):
        validity = "withdrawn"
        note = "最新版本标注撤回"
    elif effective_to and today > effective_to:
        validity = "expired"
        note = "标注失效日期已过"
    elif len(ordered) > 1:
        validity = "in_force"
        note = f"共 {len(ordered)} 个版本，旧版本保留为 superseded，不删除"
    else:
        validity = "in_force"
        note = None

    if source_health != "healthy":
        # A fetch/parse failure must always be visible, even when the version
        # itself is clean — otherwise an operator sees "in_force" and assumes the
        # evidence was refreshed.
        health_note = {
            "source_anomaly": "来源抓取异常，但异常不等于政策废止",
            "parse_failed": "原文解析失败，证据不完整，但异常不等于政策废止",
            "attachment_missing": "附件缺失，证据不完整",
            "unverified": "来源尚未核验",
        }.get(source_health, f"来源状态异常（{source_health}）")
        note = f"{note}；{health_note}" if note else health_note

    return PolicyEvidenceState(
        policy_id=str(latest.get("policy_id") or "unknown"),
        policy_version_id=latest_id,
        validity=validity,
        version_hash=str(latest.get("content_hash") or ""),
        effective_from=_as_date(latest.get("effective_from")),
        effective_to=effective_to,
        published_at=_as_date(latest.get("published_at")),
        source_health=source_health,
        superseded_by=None,
        amending_docs=tuple(
            str(row.get("document_id"))
            for row in ordered
            if row.get("document_type") in AMENDING_DOC_TYPES and row.get("document_id")
        ),
        note=note,
    )


def superseded_versions(versions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return old versions with an explicit pointer to their successor."""
    ordered = sorted(
        versions,
        key=lambda row: (
            _as_date(row.get("effective_from")) or _as_date(row.get("published_at")) or date.min,
            str(row.get("version_id") or ""),
        ),
    )
    out: list[dict[str, Any]] = []
    for index, row in enumerate(ordered[:-1]):
        successor = ordered[index + 1]
        out.append({
            "version_id": row.get("version_id"),
            "validity": "superseded",
            "superseded_by": successor.get("version_id"),
            "content_hash": row.get("content_hash"),
            # History is preserved, so the evidence of what was concluded then survives.
            "preserved": True,
        })
    return out


def detect_staleness(
    *,
    conclusion: Mapping[str, Any],
    current: PolicyEvidenceState,
    current_fact_digest: str,
) -> list[StalenessReason]:
    """Which prior conclusions must be re-checked after a change.

    Returns reasons rather than a boolean so the UI can say *why* a report is
    stale.  The old report is never overwritten — it is marked and re-issued.
    """
    reasons: list[StalenessReason] = []
    if conclusion.get("policy_version_id") != current.policy_version_id:
        reasons.append(StalenessReason.POLICY_VERSION_CHANGED)
    if conclusion.get("policy_version_hash") and conclusion.get("policy_version_hash") != current.version_hash:
        reasons.append(StalenessReason.POLICY_VERSION_CHANGED)
    if conclusion.get("fact_digest") and conclusion.get("fact_digest") != current_fact_digest:
        reasons.append(StalenessReason.FACT_CHANGED)
    if conclusion.get("fact_conflict"):
        reasons.append(StalenessReason.FACT_CONFLICTED)
    if current.validity == "withdrawn":
        reasons.append(StalenessReason.POLICY_WITHDRAWN)
    if current.source_health in {"source_anomaly", "parse_failed"}:
        reasons.append(StalenessReason.SOURCE_ANOMALY)
    window_state = conclusion.get("window_state")
    if window_state and conclusion.get("window_state_now") and window_state != conclusion.get("window_state_now"):
        reasons.append(StalenessReason.WINDOW_CHANGED)
    return sorted(set(reasons), key=str)


def fact_digest(facts: Mapping[str, Any]) -> str:
    """Stable digest of the fact snapshot used for a conclusion."""
    simplified = {}
    for key, value in sorted(facts.items()):
        if isinstance(value, Mapping):
            simplified[key] = {
                "value": value.get("value"),
                "period": value.get("period"),
                "status": value.get("status"),
            }
        else:
            simplified[key] = value
    import json

    return hashlib.sha256(
        json.dumps(simplified, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def evidence_status_label(source_health: str) -> str:
    """Map internal health to the six-state vocabulary used in reporting."""
    return {
        "healthy": "已采到原文",
        "source_anomaly": "来源异常",
        "attachment_missing": "附件缺失",
        "parse_failed": "解析失败",
        "unverified": "已登记",
    }.get(source_health, "已登记")
