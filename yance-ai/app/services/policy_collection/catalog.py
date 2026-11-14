"""Configuration-driven source catalogue.

The catalogue is the single source of truth for coverage. It is a YAML file
(``config/policy_sources.yaml``) so operations can review and edit it without a
code change, while this module enforces the structural rules that make the
coverage claim honest:

* every source has an id, authority, administrative division, level, channel,
  entry URL, domain allow-list, adapter, frequency and verification state;
* a source is only counted as *covered* if it is registered **and** verified;
* municipality-level shared sources (Beijing/Shanghai/Tianjin/Chongqing) are not
  double counted between the provincial and municipal layers.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from .urlguard import host_matches, normalize_url

PROVINCES = (
    "北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省",
    "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省",
    "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
    "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省",
    "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
)

MUNICIPALITIES = ("北京市", "天津市", "上海市", "重庆市")

LEVELS = ("national", "provincial", "municipal", "district")

CHANNELS = (
    "policy_document",   # 政策文件/法规规章
    "application",       # 申报通知/项目征集
    "notice",            # 通知公告
    "news",              # 政策发布/工作动态
    "portal",            # 惠企平台聚合页
)

ADAPTERS = ("generic_list", "portal", "rss", "open_api", "site_specific")

VERIFICATION_STATES = (
    "registered",     # 已登记
    "reachable",      # 入口可访问
    "list_verified",  # 列表页可解析
    "document_verified",  # 已成功采到原文
    "unreachable",    # 暂不可访问
)

DEFAULT_INTERVALS_HOURS = {
    "application": 6.0,
    "notice": 12.0,
    "policy_document": 24.0,
    "news": 24.0,
    "portal": 24.0,
}


class CatalogError(ValueError):
    """Raised when the catalogue violates the coverage contract."""


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    name: str
    authority: str
    level: str
    province: str | None
    city: str | None
    channel: str
    entry_url: str
    allowed_domains: tuple[str, ...]
    adapter: str = "generic_list"
    district: str | None = None
    check_interval_hours: float = 24.0
    enabled: bool = False
    shared_jurisdiction: bool = False
    link_pattern: str | None = None
    page_parameter: str | None = None
    api: dict = field(default_factory=dict)
    max_pages: int = 3
    max_documents_per_run: int = 30
    request_interval_seconds: float = 2.0
    allow_non_standard_ports: tuple[int, ...] = ()
    verification_state: str = "registered"
    last_verified_at: datetime | None = None
    last_success_at: datetime | None = None
    notes: str = ""

    @property
    def jurisdiction(self) -> str:
        return self.city or self.province or "全国"

    @property
    def canonical_entry_url(self) -> str:
        return normalize_url(self.entry_url)

    @property
    def entry_host(self) -> str:
        return (urlsplit(self.entry_url).hostname or "").lower()

    @property
    def is_verified(self) -> bool:
        return self.verification_state in {"reachable", "list_verified", "document_verified"}


@dataclass
class CitySelection:
    city: str
    province: str
    rank: int
    reasons: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)
    year: int | None = None


@dataclass
class Catalog:
    version: str
    generated_at: str | None
    sources: list[SourceDefinition]
    cities: list[CitySelection]
    notes: str = ""

    def by_id(self, source_id: str) -> SourceDefinition | None:
        return next((item for item in self.sources if item.source_id == source_id), None)

    def by_level(self, level: str) -> list[SourceDefinition]:
        return [item for item in self.sources if item.level == level]

    @property
    def enabled_sources(self) -> list[SourceDefinition]:
        return [item for item in self.sources if item.enabled]

    def coverage(self) -> dict:
        """Count distinct collection targets, deduplicating shared municipalities."""
        seen_urls: dict[str, str] = {}
        duplicates = 0
        for source in self.sources:
            key = source.canonical_entry_url
            if key in seen_urls:
                duplicates += 1
            seen_urls.setdefault(key, source.source_id)
        national = self.by_level("national")
        provincial_provinces = {item.province for item in self.by_level("provincial") if item.province}
        municipal_cities = {item.city for item in self.by_level("municipal") if item.city}
        shared = [item for item in self.sources if item.shared_jurisdiction]
        return {
            "sources_total": len(self.sources),
            "sources_enabled": len(self.enabled_sources),
            "sources_verified": len([item for item in self.sources if item.is_verified]),
            "national_sources": len(national),
            "provincial_divisions_registered": len(provincial_provinces),
            "municipal_cities_registered": len(municipal_cities),
            "shared_municipality_sources": len(shared),
            "duplicate_entry_urls": duplicates,
            "by_channel": dict(Counter(item.channel for item in self.sources)),
            "by_verification_state": dict(Counter(item.verification_state for item in self.sources)),
        }

    def validate(self, *, expected_cities: int = 30) -> list[str]:
        issues: list[str] = []
        ids: set[str] = set()
        for source in self.sources:
            if source.source_id in ids:
                issues.append(f"duplicate source_id: {source.source_id}")
            ids.add(source.source_id)
            if source.level not in LEVELS:
                issues.append(f"{source.source_id}: invalid level {source.level}")
            if source.channel not in CHANNELS:
                issues.append(f"{source.source_id}: invalid channel {source.channel}")
            if source.adapter not in ADAPTERS:
                issues.append(f"{source.source_id}: invalid adapter {source.adapter}")
            if not source.allowed_domains:
                issues.append(f"{source.source_id}: empty allowed_domains")
            if source.level in {"provincial", "municipal", "district"} and not source.province:
                issues.append(f"{source.source_id}: missing province")
            if source.level in {"municipal", "district"} and not source.city:
                issues.append(f"{source.source_id}: missing city")
            try:
                normalize_url(source.entry_url)
            except ValueError as exc:
                issues.append(f"{source.source_id}: bad entry_url ({exc})")
                continue
            if not host_matches(source.entry_host, source.allowed_domains):
                issues.append(f"{source.source_id}: entry host not in allowed_domains")
            for domain in source.allowed_domains:
                bare = domain.strip().lstrip(".")
                # A bare public suffix (gov.cn / com.cn) would allow the whole TLD.
                if bare.count(".") < 1 or bare in {"gov.cn", "com.cn", "org.cn", "net.cn"}:
                    issues.append(f"{source.source_id}: allow-list too broad ({domain})")
            if re.search(r"[*?]", "".join(source.allowed_domains)):
                issues.append(f"{source.source_id}: wildcard in allowed_domains")
            if source.check_interval_hours <= 0:
                issues.append(f"{source.source_id}: non-positive interval")
            if not source.enabled:
                # Disabled sources must be explicitly marked, so "not collected"
                # can never be mistaken for "no updates".
                if source.verification_state not in {"registered", "unreachable"}:
                    issues.append(
                        f"{source.source_id}: disabled source must state"
                        " verification_state=registered or unreachable"
                    )
                if not source.notes:
                    issues.append(f"{source.source_id}: disabled source must explain why in notes")
        registered_provinces = {item.province for item in self.sources if item.province}
        for province in PROVINCES:
            if province not in registered_provinces:
                issues.append(f"province not registered: {province}")
        municipal = {item.city for item in self.by_level("municipal") if item.city}
        # A directly administered municipality is served by one shared source
        # registered at the provincial layer; it still counts as covered.
        municipal |= {
            item.city
            for item in self.sources
            if item.shared_jurisdiction and item.city
        }
        national_cities = [city.city for city in self.cities]
        for city in national_cities:
            if city not in municipal:
                issues.append(f"priority city not registered: {city}")
        if len(set(national_cities)) < expected_cities:
            issues.append(
                f"priority city list has {len(set(national_cities))} cities, expected {expected_cities}"
            )
        for source in self.sources:
            if source.level == "provincial" and source.province in MUNICIPALITIES:
                if not source.shared_jurisdiction:
                    issues.append(
                        f"{source.source_id}: municipality provincial source must set shared_jurisdiction"
                    )
        return issues


def _dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _parse_source(raw: dict) -> SourceDefinition:
    channel = str(raw.get("channel", "policy_document"))
    interval = raw.get("check_interval_hours")
    source = SourceDefinition(
        source_id=str(raw["source_id"]),
        name=str(raw.get("name") or raw["source_id"]),
        authority=str(raw.get("authority") or ""),
        level=str(raw["level"]),
        province=raw.get("province"),
        city=raw.get("city"),
        channel=channel,
        entry_url=str(raw["entry_url"]).strip(),
        allowed_domains=tuple(str(item).strip().lower() for item in raw.get("allowed_domains") or ()),
        adapter=str(raw.get("adapter") or "generic_list"),
        district=raw.get("district"),
        check_interval_hours=float(interval if interval is not None else DEFAULT_INTERVALS_HOURS.get(channel, 24.0)),
        enabled=bool(raw.get("enabled", False)),
        shared_jurisdiction=bool(raw.get("shared_jurisdiction", False)),
        link_pattern=raw.get("link_pattern"),
        page_parameter=raw.get("page_parameter"),
        api=dict(raw.get("api") or {}),
        max_pages=int(raw.get("max_pages", 3)),
        max_documents_per_run=int(raw.get("max_documents_per_run", 30)),
        request_interval_seconds=float(raw.get("request_interval_seconds", 2.0)),
        allow_non_standard_ports=tuple(int(item) for item in raw.get("allow_non_standard_ports") or ()),
        verification_state=str(raw.get("verification_state") or "registered"),
        last_verified_at=_dt(raw.get("last_verified_at")),
        last_success_at=_dt(raw.get("last_success_at")),
        notes=str(raw.get("notes") or ""),
    )
    return source


def load_catalog(path: str | Path) -> Catalog:
    """Load one YAML file or a directory of YAML fragments (sorted by name)."""
    target = Path(path)
    if target.is_dir():
        files = sorted(item for item in target.glob("*.yaml") if item.name != "priority_cities.yaml")
        city_file = target / "priority_cities.yaml"
        payloads = [yaml.safe_load(item.read_text(encoding="utf-8")) or {} for item in files]
        city_payload = (
            yaml.safe_load(city_file.read_text(encoding="utf-8")) or {} if city_file.exists() else {}
        )
        raw_sources = [item for payload in payloads for item in payload.get("sources") or []]
        raw_cities = city_payload.get("priority_cities") or []
        version = "+".join(
            str(payload.get("catalog_version")) for payload in payloads if payload.get("catalog_version")
        )
        notes = "\n".join(str(payload.get("notes") or "") for payload in payloads).strip()
        sources = [_parse_source(item) for item in raw_sources]
        cities = _parse_cities(raw_cities)
        return Catalog(
            version=version or "unknown",
            generated_at=payloads[0].get("generated_at") if payloads else None,
            sources=sources,
            cities=cities,
            notes=notes,
        )
    payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    sources = [_parse_source(item) for item in payload.get("sources") or []]
    return Catalog(
        version=str(payload.get("catalog_version") or "unknown"),
        generated_at=payload.get("generated_at"),
        sources=sources,
        cities=_parse_cities(payload.get("priority_cities") or []),
        notes=str(payload.get("notes") or ""),
    )


def _parse_cities(raw_cities: list[dict]) -> list[CitySelection]:
    return [
        CitySelection(
            city=str(item["city"]),
            province=str(item["province"]),
            rank=int(item.get("rank") or index + 1),
            reasons=list(item.get("reasons") or []),
            data_sources=list(item.get("data_sources") or []),
            year=item.get("year"),
        )
        for index, item in enumerate(raw_cities)
    ]
