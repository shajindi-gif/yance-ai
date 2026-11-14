"""Park registry: configuration-driven catalogue with honest coverage accounting.

The YAML files under ``config/parks`` are the single source of truth for which
parks exist in the system.  This module only enforces structure; it never
invents a park, a district or a boundary.

Two rules are encoded here because they are the most common way a "park policy"
product silently becomes wrong:

1. **A park is not a policy scope.**  Registering a park says nothing about which
   enterprises a policy covers.  Scope lives in ``park_policy_scopes`` and needs
   its own upstream evidence.
2. **A place is not a qualification.**  ``boundary_status`` cannot be raised to
   ``confirmed`` by a name match.  Anything unverified stays
   ``needs_confirmation`` and the API must surface it that way.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

PARK_TYPES = (
    "national_high_tech_zone",
    "provincial_high_tech_zone",
    "science_city",
    "tech_city",
    "tech_park",
    "economic_dev_zone",
    "incubator",
    "other_carrier",
)

PARK_TYPE_LABELS = {
    "national_high_tech_zone": "国家高新区",
    "provincial_high_tech_zone": "省级高新区",
    "science_city": "科学城",
    "tech_city": "科技城",
    "tech_park": "科技园区",
    "economic_dev_zone": "经济技术开发区",
    "incubator": "孵化器/众创空间",
    "other_carrier": "其他科创载体",
}

PARK_STATUS = ("active", "renamed", "merged", "abolished", "unknown")
BOUNDARY_STATUS = ("confirmed", "partial", "needs_confirmation")
VERIFICATION_STATES = ("registered", "reachable", "metadata_verified", "unreachable")

REQUIRED_FIELDS = (
    "park_id",
    "name",
    "park_type",
    "province",
    "city",
    "status",
    "boundary_status",
    "verification_status",
)

DEFAULT_CATALOG_DIR = Path("config/parks")


class ParkCatalogError(ValueError):
    """Raised when the park catalogue is structurally invalid."""


@dataclass(frozen=True)
class ParkRecord:
    park_id: str
    name: str
    park_type: str
    province: str
    city: str
    district: str | None = None
    aliases: tuple[str, ...] = ()
    designation_level: str = "national"
    designation_basis: str | None = None
    designation_year: int | None = None
    operator: str | None = None
    official_url: str | None = None
    status: str = "active"
    boundary_status: str = "needs_confirmation"
    boundary_note: str | None = None
    source_url: str | None = None
    source_kind: str | None = None
    verification_status: str = "registered"
    verified_at: datetime | None = None
    verification_note: str | None = None
    confidence: float | None = None
    catalog_version: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def type_label(self) -> str:
        return PARK_TYPE_LABELS.get(self.park_type, self.park_type)

    @property
    def is_usable_for_matching(self) -> bool:
        """A park may only drive matching once its boundary question is settled."""
        return self.status == "active" and self.boundary_status == "confirmed"

    def to_model_kwargs(self) -> dict[str, Any]:
        return {
            "park_id": self.park_id,
            "name": self.name,
            "aliases": list(self.aliases),
            "park_type": self.park_type,
            "designation_level": self.designation_level,
            "designation_basis": self.designation_basis,
            "designation_year": self.designation_year,
            "province": self.province,
            "city": self.city,
            "district": self.district,
            "operator": self.operator,
            "official_url": self.official_url,
            "status": self.status,
            "boundary_status": self.boundary_status,
            "boundary_note": self.boundary_note,
            "source_url": self.source_url,
            "source_kind": self.source_kind,
            "verification_status": self.verification_status,
            "verified_at": self.verified_at,
            "verification_note": self.verification_note,
            "catalog_version": self.catalog_version,
            "confidence": self.confidence,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class ParkCatalog:
    catalog_version: str
    records: tuple[ParkRecord, ...]
    source_files: tuple[str, ...]
    digest: str

    def by_id(self) -> dict[str, ParkRecord]:
        return {item.park_id: item for item in self.records}

    def by_city(self) -> dict[tuple[str, str], list[ParkRecord]]:
        grouped: dict[tuple[str, str], list[ParkRecord]] = {}
        for item in self.records:
            grouped.setdefault((item.province, item.city), []).append(item)
        return grouped

    def coverage(self) -> dict[str, Any]:
        """Coverage by type / verification state.

        ``registered`` is *not* coverage.  Only ``metadata_verified`` counts as a
        verified entry, and the report states that explicitly.
        """
        type_counter = Counter(item.park_type for item in self.records)
        verification_counter = Counter(item.verification_status for item in self.records)
        boundary_counter = Counter(item.boundary_status for item in self.records)
        province_counter = Counter(item.province for item in self.records)
        return {
            "catalog_version": self.catalog_version,
            "total_registered": len(self.records),
            "by_type": {PARK_TYPE_LABELS.get(k, k): v for k, v in sorted(type_counter.items())},
            "by_verification": dict(sorted(verification_counter.items())),
            "by_boundary": dict(sorted(boundary_counter.items())),
            "provinces_covered": len(province_counter),
            "cities_covered": len({(i.province, i.city) for i in self.records}),
            "metadata_verified": verification_counter.get("metadata_verified", 0),
            "usable_for_matching": sum(1 for item in self.records if item.is_usable_for_matching),
            "note": (
                "registered 仅表示已登记，不等于已连通或已核验；"
                "boundary_status=confirmed 之前，该园区不参与企业-园区匹配。"
            ),
            "digest": self.digest,
        }


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _as_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def load_catalog(catalog_dir: Path | str | None = None) -> ParkCatalog:
    """Load and validate every ``*.yaml`` file in the park catalogue directory."""
    base = Path(catalog_dir) if catalog_dir else DEFAULT_CATALOG_DIR
    if not base.exists():
        raise ParkCatalogError(f"园区目录不存在: {base}")

    # Accept a single YAML file as well as a directory.  Previously a file path made
    # ``glob`` return nothing and produced the misleading "catalog_version 不一致: []".
    if base.is_file():
        yaml_files = [base] if base.suffix in {".yaml", ".yml"} else []
        if not yaml_files:
            raise ParkCatalogError(f"园区目录文件必须是 .yaml/.yml: {base}")
    else:
        yaml_files = sorted(base.glob("*.yaml"))
        if not yaml_files:
            raise ParkCatalogError(f"园区目录下没有 yaml 文件: {base}")

    records: list[ParkRecord] = []
    versions: set[str] = set()
    files: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_names: dict[str, str] = {}

    for path in yaml_files:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ParkCatalogError(f"{path.name}: 顶层必须是映射")
        version = raw.get("catalog_version")
        if not version:
            raise ParkCatalogError(f"{path.name}: 缺少 catalog_version")
        versions.add(str(version))
        files.append(path.name)

        parks = raw.get("parks")
        if not isinstance(parks, list) or not parks:
            raise ParkCatalogError(f"{path.name}: parks 必须是非空列表")

        for item in parks:
            if not isinstance(item, dict):
                raise ParkCatalogError(f"{path.name}: parks 条目必须是映射")
            missing = [key for key in REQUIRED_FIELDS if not item.get(key)]
            if missing:
                raise ParkCatalogError(
                    f"{path.name}: {item.get('park_id') or item.get('name') or '?'} 缺少字段 {missing}"
                )
            park_type = item["park_type"]
            if park_type not in PARK_TYPES:
                raise ParkCatalogError(f"{path.name}: 未知 park_type={park_type}")
            if item["status"] not in PARK_STATUS:
                raise ParkCatalogError(f"{path.name}: 未知 status={item['status']}")
            if item["boundary_status"] not in BOUNDARY_STATUS:
                raise ParkCatalogError(f"{path.name}: 未知 boundary_status={item['boundary_status']}")
            if item["verification_status"] not in VERIFICATION_STATES:
                raise ParkCatalogError(
                    f"{path.name}: 未知 verification_status={item['verification_status']}"
                )

            park_id = str(item["park_id"])
            if park_id in seen_ids:
                raise ParkCatalogError(f"park_id 重复: {park_id} 同时出现在 {seen_ids[park_id]} 和 {path.name}")
            seen_ids[park_id] = path.name

            name = str(item["name"])
            if name in seen_names:
                raise ParkCatalogError(f"园区名称重复: {name}（{park_id}）")

            # Aliases must not collide across parks, otherwise matching is ambiguous.
            for alias in _as_tuple(item.get("aliases")):
                key = alias.strip()
                if not key:
                    raise ParkCatalogError(f"{path.name}: {park_id} 存在空别名")
                if key in seen_names:
                    raise ParkCatalogError(
                        f"别名冲突: {key}（{park_id}）与已登记园区 {seen_names[key]} 冲突"
                    )
                seen_names[key] = park_id
            seen_names[name] = park_id

            confidence = item.get("confidence")
            records.append(
                ParkRecord(
                    park_id=park_id,
                    name=name,
                    park_type=park_type,
                    province=str(item["province"]),
                    city=str(item["city"]),
                    district=item.get("district") or None,
                    aliases=_as_tuple(item.get("aliases")),
                    designation_level=str(item.get("designation_level") or "national"),
                    designation_basis=item.get("designation_basis"),
                    designation_year=item.get("designation_year"),
                    operator=item.get("operator"),
                    official_url=item.get("official_url") or None,
                    status=str(item["status"]),
                    boundary_status=str(item["boundary_status"]),
                    boundary_note=item.get("boundary_note"),
                    source_url=item.get("source_url"),
                    source_kind=item.get("source_kind"),
                    verification_status=str(item["verification_status"]),
                    verified_at=_parse_dt(item.get("verified_at")),
                    verification_note=item.get("verification_note"),
                    confidence=float(confidence) if confidence is not None else None,
                    catalog_version=str(version),
                    extra={
                        key: value
                        for key, value in item.items()
                        if key
                        not in {
                            "park_id", "name", "aliases", "park_type", "designation_level",
                            "designation_basis", "designation_year", "province", "city",
                            "district", "operator", "official_url", "status",
                            "boundary_status", "boundary_note", "source_url", "source_kind",
                            "verification_status", "verified_at", "verification_note",
                            "confidence",
                        }
                    },
                )
            )

    # A park whose type is a "zone" must not silently claim a confirmed boundary
    # without a source.  This is a structural guard, not a judgement about truth.
    for record in records:
        if record.boundary_status == "confirmed" and not record.source_url:
            raise ParkCatalogError(
                f"{record.park_id}: boundary_status=confirmed 必须提供 source_url"
            )

    digest = hashlib.sha256(
        json.dumps(
            [r.to_model_kwargs() | {"verified_at": r.verified_at.isoformat() if r.verified_at else None}
             for r in records],
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()

    if len(versions) != 1:
        raise ParkCatalogError(f"多个文件 catalog_version 不一致: {sorted(versions)}")

    return ParkCatalog(
        catalog_version=next(iter(versions)),
        records=tuple(records),
        source_files=tuple(files),
        digest=digest,
    )


def find_parks(
    catalog: ParkCatalog,
    *,
    province: str | None = None,
    city: str | None = None,
    park_type: str | None = None,
    include_inactive: bool = False,
) -> list[ParkRecord]:
    result = []
    for record in catalog.records:
        if not include_inactive and record.status != "active":
            continue
        if province and record.province != province:
            continue
        if city and record.city != city:
            continue
        if park_type and record.park_type != park_type:
            continue
        result.append(record)
    return result


def match_park_by_name(catalog: ParkCatalog, text: str) -> list[ParkRecord]:
    """Exact name/alias lookup only.

    Substring matching is deliberately *not* used: "苏州" appears inside both
    苏州高新区 and 苏州工业园区, and fuzzy matching would silently assign an
    enterprise to the wrong park's policy regime.
    """
    needle = (text or "").strip()
    if not needle:
        return []
    hits = []
    for record in catalog.records:
        if record.name == needle or needle in record.aliases:
            hits.append(record)
    return hits


def iteration(records: Iterable[ParkRecord]) -> list[dict[str, Any]]:
    return [record.to_model_kwargs() for record in records]
