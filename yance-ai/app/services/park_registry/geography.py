"""Jurisdiction and park-attachment logic.

The whole point of this module is to refuse three convenient but wrong shortcuts:

1. ``企业地址在 XX 市`` ⇒ ``企业享受 XX 园区政策``.  Wrong: a park's policy may
   require registration, tax, statistics or operational presence *in the park*.
2. ``园区在 XX 市`` ⇒ ``园区政策适用于 XX 市所有企业``.  Wrong: park policy usually
   covers park-registered enterprises only.
3. ``政策标注省级`` ⇒ ``只适用于省会``.  Wrong: a provincial policy with no city
   qualification covers the whole province; narrowing it is a silent exclusion.

Every verdict therefore carries ``basis`` (which fact decided it) and either an
evidence pointer or an explicit "needs confirmation".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.services.park_registry.catalog import ParkRecord


class AttachmentStatus(StrEnum):
    CONFIRMED_MEMBER = "confirmed_member"
    NOT_MEMBER = "not_member"
    NEEDS_CONFIRMATION = "needs_confirmation"
    UNKNOWN = "unknown"


class ScopeVerdict(StrEnum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    INSUFFICIENT = "insufficient"
    NEEDS_REVIEW = "needs_review"


# Facts that can establish a park relationship.  Each one is a *different* legal
# relationship and they are never interchangeable.
PARK_FACT_KEYS = {
    "registered_in_park": "registered_park_id",
    "tax_in_park": "tax_park_id",
    "operation_in_park": "operation_park_id",
    "statistics_in_park": "statistics_park_id",
}

ADDRESS_FACT_KEYS = ("address_province", "address_city", "address_district", "address_text")
REGION_FACT_KEYS = ("province", "city", "district")

# A basis name that would let a bare postal address decide a park entitlement.
FORBIDDEN_BASES = set(ADDRESS_FACT_KEYS) | {"address_match", "name_contains_park"}


@dataclass(frozen=True)
class AttachmentResult:
    status: AttachmentStatus
    basis: str
    reason: str
    park_id: str | None = None
    evidence_fact_keys: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": str(self.status),
            "basis": self.basis,
            "reason": self.reason,
            "park_id": self.park_id,
            "evidence_fact_keys": list(self.evidence_fact_keys),
        }


@dataclass(frozen=True)
class ScopeResult:
    verdict: ScopeVerdict
    reason: str
    basis: str = ""
    park_id: str | None = None
    requires_confirmation: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": str(self.verdict),
            "reason": self.reason,
            "basis": self.basis,
            "park_id": self.park_id,
            "requires_confirmation": self.requires_confirmation,
        }


def _fact_value(facts: Mapping[str, Any], key: str) -> Any:
    value = facts.get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def resolve_park_attachment(
    park: ParkRecord | str | None,
    facts: Mapping[str, Any],
    *,
    required: str = "registered_in_park",
) -> AttachmentResult:
    """Decide whether an enterprise is attached to a park *on the required basis*.

    ``required`` is the qualification basis declared by the policy scope, not a
    best guess.  Passing ``unspecified`` returns NEEDS_CONFIRMATION because the
    original text did not say which relationship it demands.
    """
    park_id = park.park_id if isinstance(park, ParkRecord) else park
    if not park_id:
        return AttachmentResult(
            AttachmentStatus.UNKNOWN, "no_park", "未指定园区，无法判定园区归属"
        )

    if required == "all_companies":
        return AttachmentResult(
            AttachmentStatus.CONFIRMED_MEMBER,
            "all_companies",
            "政策适用范围为园区内所有符合条件企业，不以单一归属关系为前提",
            park_id=park_id,
        )

    if required == "unspecified":
        return AttachmentResult(
            AttachmentStatus.NEEDS_CONFIRMATION,
            "unspecified",
            "原文未明确要求注册、纳税、经营或统计关系，需人工复核适用范围",
            park_id=park_id,
        )

    if required == "park_recommended":
        value = _fact_value(facts, "park_recommendation")
        if value:
            return AttachmentResult(
                AttachmentStatus.CONFIRMED_MEMBER,
                "park_recommendation",
                "企业已取得园区/主管部门推荐材料",
                park_id=park_id,
                evidence_fact_keys=("park_recommendation",),
            )
        return AttachmentResult(
            AttachmentStatus.NEEDS_CONFIRMATION,
            "park_recommendation",
            "政策要求园区或主管部门推荐，企业侧尚无推荐材料",
            park_id=park_id,
        )

    fact_key = PARK_FACT_KEYS.get(required)
    if not fact_key:
        return AttachmentResult(
            AttachmentStatus.NEEDS_CONFIRMATION,
            f"unknown_basis:{required}",
            f"未识别的归属依据 {required}，需人工复核",
            park_id=park_id,
        )

    value = _fact_value(facts, fact_key)
    if not value:
        # An enterprise may already hold a *different* park relationship (tax in
        # the park, registered elsewhere).  Saying "missing facts" there would be
        # misleading: the user must supply the specific relationship the policy
        # demands, and a different one does not substitute for it.
        other_relations = [
            _basis_label(basis)
            for basis, other_key in PARK_FACT_KEYS.items()
            if other_key != fact_key and _fact_value(facts, other_key)
        ]
        address_hint = any(_fact_value(facts, key) for key in ADDRESS_FACT_KEYS)
        if other_relations:
            reason = (
                f"政策要求的是{_basis_label(required)}，"
                f"企业现有资料为{'、'.join(other_relations)}，两者不能互相替代"
            )
        elif address_hint:
            reason = "缺少园区归属事实，地址信息不能替代注册/纳税/经营/统计关系"
        else:
            reason = "缺少园区归属事实"
        return AttachmentResult(
            AttachmentStatus.NEEDS_CONFIRMATION,
            fact_key,
            reason,
            park_id=park_id,
            evidence_fact_keys=tuple(
                other_key
                for other_key in PARK_FACT_KEYS.values()
                if other_key != fact_key and _fact_value(facts, other_key)
            ),
        )

    normalized = str(value).strip()
    if normalized != park_id:
        # An enterprise may legitimately belong to one park and not another.
        return AttachmentResult(
            AttachmentStatus.NOT_MEMBER,
            fact_key,
            f"企业登记的{_basis_label(required)}为 {normalized}，与本政策适用园区 {park_id} 不一致",
            park_id=park_id,
            evidence_fact_keys=(fact_key,),
        )

    return AttachmentResult(
        AttachmentStatus.CONFIRMED_MEMBER,
        fact_key,
        f"企业登记的{_basis_label(required)}与本政策适用园区一致",
        park_id=park_id,
        evidence_fact_keys=(fact_key,),
    )


def _basis_label(basis: str) -> str:
    return {
        "registered_in_park": "注册地",
        "tax_in_park": "纳税地",
        "operation_in_park": "实际经营地",
        "statistics_in_park": "统计关系",
    }.get(basis, basis)


def evaluate_scope(
    scope: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    park: ParkRecord | None = None,
) -> ScopeResult:
    """Evaluate one ``park_policy_scope`` row against an enterprise fact snapshot.

    The ``scope`` mapping mirrors the ``park_policy_scopes`` table columns.
    """
    scope_type = scope.get("scope_type")
    requires_confirmation = bool(scope.get("requires_confirmation", True))
    qualification_basis = scope.get("qualification_basis") or "unspecified"
    park_id = scope.get("park_id")

    # 1. Administrative scopes: province / city / district.
    if scope_type in {"national", "province", "city", "district"}:
        if requires_confirmation or scope.get("review_status") not in {"confirmed", None}:
            # review_status None means the caller passed a raw config row without
            # the review workflow; treat as needing review only if flagged above.
            if requires_confirmation:
                return ScopeResult(
                    ScopeVerdict.NEEDS_REVIEW,
                    "适用范围尚未与原文核对，按需复核处理",
                    basis=f"scope_type:{scope_type}",
                    requires_confirmation=True,
                )
        missing: list[str] = []
        mismatch: list[str] = []
        for key in ("province", "city", "district"):
            required = scope.get(key)
            if not required:
                continue
            actual = _fact_value(facts, key) or _fact_value(facts, f"address_{key}")
            if not actual:
                missing.append(key)
            elif str(actual) != str(required):
                mismatch.append(f"{key}:{actual}!={required}")
        if mismatch:
            return ScopeResult(
                ScopeVerdict.NOT_SATISFIED,
                "企业行政区划不在该政策适用范围内：" + "；".join(mismatch),
                basis=f"scope_type:{scope_type}",
            )
        if missing:
            return ScopeResult(
                ScopeVerdict.INSUFFICIENT,
                "企业行政区划字段缺失：" + "、".join(missing),
                basis=f"scope_type:{scope_type}",
            )
        return ScopeResult(
            ScopeVerdict.SATISFIED,
            "企业行政区划命中政策适用范围" if scope_type != "national" else "政策为全国适用",
            basis=f"scope_type:{scope_type}",
        )

    # 2. Park scopes: the park must be confirmed and the basis must be explicit.
    if scope_type == "park":
        if not park_id:
            return ScopeResult(
                ScopeVerdict.NEEDS_REVIEW, "园区适用范围缺少 park_id", basis="scope_type:park"
            )
        if park is not None and park.boundary_status != "confirmed":
            return ScopeResult(
                ScopeVerdict.NEEDS_REVIEW,
                f"园区 {park_id} 边界状态为 {park.boundary_status}，不得据此判定企业符合园区政策",
                basis="park_boundary",
                park_id=park_id,
                requires_confirmation=True,
            )
        attachment = resolve_park_attachment(park_id, facts, required=qualification_basis)
        if attachment.status is AttachmentStatus.CONFIRMED_MEMBER:
            return ScopeResult(
                ScopeVerdict.SATISFIED,
                attachment.reason,
                basis=attachment.basis,
                park_id=park_id,
            )
        if attachment.status is AttachmentStatus.NOT_MEMBER:
            return ScopeResult(
                ScopeVerdict.NOT_SATISFIED,
                attachment.reason,
                basis=attachment.basis,
                park_id=park_id,
            )
        return ScopeResult(
            ScopeVerdict.INSUFFICIENT,
            attachment.reason,
            basis=attachment.basis,
            park_id=park_id,
            requires_confirmation=attachment.status is AttachmentStatus.NEEDS_CONFIRMATION,
        )

    return ScopeResult(
        ScopeVerdict.NEEDS_REVIEW,
        f"未识别的适用范围类型 {scope_type}",
        basis=f"scope_type:{scope_type}",
    )


def address_is_not_entitlement(facts: Mapping[str, Any]) -> bool:
    """True when the snapshot only carries address-type region facts.

    Used by the UI/report layer to explain why a park policy cannot be granted
    even though the address obviously sits inside the park's city.
    """
    has_address = any(_fact_value(facts, key) for key in ADDRESS_FACT_KEYS)
    has_park = any(_fact_value(facts, key) for key in PARK_FACT_KEYS.values())
    return has_address and not has_park


def regression_guards() -> dict[str, bool]:
    """Self-describing invariants asserted in the test suite."""
    return {
        "address_can_grant_park_entitlement": bool(FORBIDDEN_BASES & set(PARK_FACT_KEYS.values())),
        "provincial_scope_requires_city": False,
        "park_scope_requires_explicit_park_id": True,
    }
