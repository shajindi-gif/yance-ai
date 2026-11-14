"""Park registry, policy scope and evidence-conditioned eligibility tables.

Design constraints
------------------
* **Additive only.**  Four new tables; no existing column is altered, so an older
  application build keeps working against a migrated database and the rollback
  path is "stop using the new screens", not "restore the database".
* **A park location is not a policy scope.**  ``parks`` describes where a park is
  and what designates it; ``park_policy_scopes`` describes which enterprises a
  policy actually covers.  The two are deliberately separate tables so a policy
  can require registration / tax / statistics / operation in a park without the
  system ever inferring that from an address string.
* **Unknown stays unknown.**  ``boundary_status`` and ``review_status`` default
  to the "needs confirmation" side.  Nothing is promoted to ``confirmed`` by
  inference alone.
* **Evidence is addressable.**  Every ``PolicyCondition`` carries the clause
  reference and the verbatim quote plus character offsets, so a matrix cell can
  point back into the stored original text instead of paraphrasing it.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.models import TimestampMixin, now_utc

PARK_TYPES = (
    "national_high_tech_zone",      # 国家高新区
    "provincial_high_tech_zone",    # 省级高新区
    "science_city",                 # 科学城
    "tech_city",                    # 科技城
    "tech_park",                    # 科技园区（非高新区序列，需单独官方依据）
    "economic_dev_zone",            # 经开区
    "incubator",                    # 孵化器/众创空间
    "other_carrier",                # 其他科创载体
)

PARK_STATUS = ("active", "renamed", "merged", "abolished", "unknown")

BOUNDARY_STATUS = ("confirmed", "partial", "needs_confirmation")

PARK_VERIFICATION = (
    "registered",          # 已登记，未核验
    "reachable",           # 官网可访问
    "metadata_verified",   # 认定依据/行政区划已与官方页面核对
    "unreachable",         # 当前不可访问（网络/站点限制）
)

SCOPE_TYPES = ("national", "province", "city", "district", "park")

QUALIFICATION_BASIS = (
    "all_companies",        # 该行政区划内所有符合条件企业
    "registered_in_park",   # 要求注册在园区
    "tax_in_park",          # 要求税务登记/纳税在园区
    "operation_in_park",    # 要求实际经营场所在园区
    "statistics_in_park",   # 要求统计关系在园区
    "park_recommended",     # 需园区/主管部门推荐
    "unspecified",          # 原文未明确，需复核
)


class Park(Base, TimestampMixin):
    """A science/technology park or carrier, with its official designation basis."""

    __tablename__ = "parks"
    __table_args__ = (
        CheckConstraint("park_type IN ('national_high_tech_zone','provincial_high_tech_zone','economic_dev_zone','tech_park','science_city','incubator','other')", name='ck_parks_park_type'),
        CheckConstraint("boundary_status IN ('confirmed','needs_confirmation','partial','unknown')", name='ck_parks_boundary_status'),
        CheckConstraint("verification_status IN ('registered','reachable','metadata_verified','unreachable','withdrawn')", name='ck_parks_verification_status'),

    )

    park_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    name_en: Mapped[str | None] = mapped_column(String(240))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    park_type: Mapped[str] = mapped_column(String(40), index=True)
    designation_level: Mapped[str] = mapped_column(String(24), default="national")
    designation_basis: Mapped[str | None] = mapped_column(String(500))
    designation_year: Mapped[int | None] = mapped_column(Integer)
    province: Mapped[str] = mapped_column(String(80), index=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str | None] = mapped_column(String(80))
    admin_division_code: Mapped[str | None] = mapped_column(String(20), index=True)
    operator: Mapped[str | None] = mapped_column(String(240))
    official_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    boundary_status: Mapped[str] = mapped_column(
        String(24), default="needs_confirmation", index=True
    )
    boundary_note: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_kind: Mapped[str | None] = mapped_column(String(40))
    verification_status: Mapped[str] = mapped_column(
        String(24), default="registered", index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_note: Mapped[str | None] = mapped_column(String(500))
    catalog_version: Mapped[str | None] = mapped_column(String(40))
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    history: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)


class ParkPolicyScope(Base, TimestampMixin):
    """Which enterprises a policy actually covers — evidence required, inference forbidden."""

    __tablename__ = "park_policy_scopes"
    __table_args__ = (
        CheckConstraint("scope_type IN ('national','province','city','district','park')", name='ck_park_policy_scopes_scope_type'),
        CheckConstraint("qualification_basis IN ('registered_in_park','tax_in_park','operating_in_park','statistical_in_park','unspecified')", name='ck_park_policy_scopes_qualification_basis'),
        CheckConstraint("scope_type <> 'park' OR park_id IS NOT NULL", name='ck_park_policy_scopes_park_requires_id'),
        UniqueConstraint(
            "policy_id", "scope_key", name="uq_park_policy_scope_key"
        ),
        Index("ix_park_policy_scopes_park", "park_id", "review_status"),
        Index("ix_park_policy_scopes_policy", "policy_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="SET NULL"), index=True
    )
    scope_key: Mapped[str] = mapped_column(String(200))
    scope_type: Mapped[str] = mapped_column(String(24), index=True)
    park_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("parks.park_id", ondelete="SET NULL"), index=True
    )
    province: Mapped[str | None] = mapped_column(String(80), index=True)
    city: Mapped[str | None] = mapped_column(String(80), index=True)
    district: Mapped[str | None] = mapped_column(String(80))
    qualification_basis: Mapped[str] = mapped_column(String(40), default="unspecified")
    applies_to_all_enterprises: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    clause_ref: Mapped[str | None] = mapped_column(String(120))
    evidence_text: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    review_status: Mapped[str] = mapped_column(String(24), default="needs_review", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicyCondition(Base, TimestampMixin):
    """One addressable eligibility condition extracted from a policy clause."""

    __tablename__ = "policy_conditions"
    __table_args__ = (
        CheckConstraint("group_logic IN ('all','any')", name='ck_policy_conditions_group_logic'),
        CheckConstraint("operator IN ('gte','lte','eq','ne','in','not_in','between','exists','matches')", name='ck_policy_conditions_operator'),
        CheckConstraint('quote_char_start IS NULL OR quote_char_end IS NULL OR quote_char_end >= quote_char_start', name='ck_policy_conditions_quote_span'),
        Index("ix_policy_conditions_policy_group", "policy_id", "group_key"),
        Index("ix_policy_conditions_version", "policy_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="SET NULL"), index=True
    )
    condition_key: Mapped[str] = mapped_column(String(200))
    group_key: Mapped[str] = mapped_column(String(80), default="主体资格", index=True)
    group_logic: Mapped[str] = mapped_column(String(16), default="all")
    fact_key: Mapped[str] = mapped_column(String(120), index=True)
    operator: Mapped[str] = mapped_column(String(16), default="exists")
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)
    unit: Mapped[str | None] = mapped_column(String(40))
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str] = mapped_column(String(40), default="other", index=True)
    clause_ref: Mapped[str | None] = mapped_column(String(120))
    quote: Mapped[str] = mapped_column(Text, default="")
    quote_char_start: Mapped[int | None] = mapped_column(Integer)
    quote_char_end: Mapped[int | None] = mapped_column(Integer)
    extraction_method: Mapped[str] = mapped_column(String(40), default="manual")
    review_status: Mapped[str] = mapped_column(String(24), default="needs_review", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)


class PolicyEvalRun(Base, TimestampMixin):
    """A reproducible comparison run (arm A/B/C) against a frozen, hashed dataset."""

    __tablename__ = "policy_eval_runs"
    __table_args__ = (
        CheckConstraint("arm IN ('A','B','C')", name='ck_policy_eval_runs_arm'),
        Index("ix_policy_eval_runs_dataset_arm", "dataset_version", "arm"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version: Mapped[str] = mapped_column(String(60), index=True)
    dataset_sha256: Mapped[str] = mapped_column(String(64))
    arm: Mapped[str] = mapped_column(String(8), index=True)
    runner: Mapped[str] = mapped_column(String(60))
    model_id: Mapped[str | None] = mapped_column(String(120))
    model_version: Mapped[str | None] = mapped_column(String(120))
    online_search_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tools_enabled: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    model_calls: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[float | None] = mapped_column(Numeric(12, 4))
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    case_results: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
