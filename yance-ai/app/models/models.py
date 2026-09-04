import enum
import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class TenantOwnedMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )


class UserRole(enum.StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "users"
    __table_args__ = (Index("uq_users_tenant_email", "tenant_id", "email", unique=True),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.member)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Membership(Base, TimestampMixin, TenantOwnedMixin):
    """Compatibility layer for future multi-workspace identity."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    status: Mapped[str] = mapped_column(String(40), default="active")


class Company(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "companies"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(240))
    unified_credit_code: Mapped[str | None] = mapped_column(String(64))
    province: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(80))
    industry: Mapped[str | None] = mapped_column(String(160))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class CompanyProfile(Base, TimestampMixin, TenantOwnedMixin):
    """Mutable draft and pointer metadata for immutable company profile versions."""

    __tablename__ = "company_profiles"
    __table_args__ = (UniqueConstraint("company_id", name="uq_company_profile_company"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="draft")
    draft_json: Mapped[dict] = mapped_column(JSON, default=dict)
    completeness_score: Mapped[int] = mapped_column(default=0)
    published_version: Mapped[int | None]
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CompanyProfileVersion(Base, TenantOwnedMixin):
    """Immutable profile snapshot pinned by scans and later decision records."""

    __tablename__ = "company_profile_versions"
    __table_args__ = (
        UniqueConstraint("profile_id", "version", name="uq_company_profile_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_profiles.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int]
    snapshot_json: Mapped[dict] = mapped_column(JSON)
    completeness_score: Mapped[int]
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class CompanyFact(Base, TimestampMixin, TenantOwnedMixin):
    """Typed fact projection for a published profile version."""

    __tablename__ = "company_facts"
    __table_args__ = (
        UniqueConstraint("profile_version_id", "fact_key", name="uq_company_fact_version_key"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_profile_versions.id", ondelete="CASCADE"),
        index=True,
    )
    fact_key: Mapped[str] = mapped_column(String(120))
    value_json: Mapped[dict] = mapped_column(JSON)
    unit: Mapped[str | None] = mapped_column(String(40))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    extraction_method: Mapped[str] = mapped_column(String(40), default="user_asserted")
    verification_status: Mapped[str] = mapped_column(String(40), default="unverified")


class Document(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    object_key: Mapped[str] = mapped_column(String(700), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="pending_upload")
    size_bytes: Mapped[int | None]
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_type: Mapped[str] = mapped_column(String(40), default="file")
    ingestion_status: Mapped[str] = mapped_column(String(40), default="not_requested", index=True)
    ingestion_error: Mapped[str | None] = mapped_column(String(240))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Policy(Base, TimestampMixin):
    """Global Policy Knowledge Base — platform-level, shared by all tenants."""

    __tablename__ = "policies"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(500))
    issuing_authority: Mapped[str | None] = mapped_column(String(240))  # 发文机关
    level: Mapped[str | None] = mapped_column(
        String(40), index=True
    )  # national/provincial/municipal/district
    province: Mapped[str | None] = mapped_column(String(80), index=True)
    city: Mapped[str | None] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(80))
    industry: Mapped[str | None] = mapped_column(String(160), index=True)
    policy_type: Mapped[str | None] = mapped_column(String(80))  # subsidy/tax_break/qualification
    source_url: Mapped[str | None] = mapped_column(String(1000))
    jurisdiction: Mapped[str | None] = mapped_column(String(160))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    content: Mapped[str | None] = mapped_column(Text)
    original_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(160))
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    support_amount: Mapped[str | None] = mapped_column(String(120))  # e.g. "最高500万"
    support_type: Mapped[str | None] = mapped_column(String(120))  # 资金补贴/税收优惠/资质认定
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)


class PolicyRule(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "policy_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(300))
    rule_type: Mapped[str] = mapped_column(String(80))
    rule_json: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text)


class PolicyScan(Base, TimestampMixin, TenantOwnedMixin):
    """Persistent request/snapshot boundary for one company opportunity scan."""

    __tablename__ = "policy_scans"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_policy_scan_idempotency"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_profile_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    provider: Mapped[str | None] = mapped_column(String(40))
    total_opportunities: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(120))


class Opportunity(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "opportunities"
    __table_args__ = (UniqueConstraint("scan_id", "policy_id", name="uq_opportunity_scan_policy"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(500))
    score: Mapped[float | None]
    status: Mapped[str] = mapped_column(String(40), default="identified")
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_scans.id", ondelete="CASCADE"), index=True
    )
    profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_profile_versions.id", ondelete="SET NULL")
    )
    policy_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    eligibility_status: Mapped[str] = mapped_column(
        String(40), default="NEED_MORE_INFORMATION", index=True
    )
    eligibility_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))


class Application(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "applications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default="draft")
    form_data: Mapped[dict] = mapped_column(JSON, default=dict)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress: Mapped[int] = mapped_column(default=0)
    review_status: Mapped[str] = mapped_column(String(40), default="not_requested")


class ApplicationRequirement(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "application_requirements"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="material")
    status: Mapped[str] = mapped_column(String(40), default="missing")
    is_hard_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    source_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(default=0)


class ApplicationActivity(Base, TenantOwnedMixin):
    __tablename__ = "application_activities"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Order(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_tenant_resource", "tenant_id", "resource_type", "resource_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    product_code: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(40), default="pending")


class Payment(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    provider: Mapped[str] = mapped_column(String(40))  # "alipay" | "stripe"
    provider_trade_no: Mapped[str | None] = mapped_column(String(128), unique=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    stripe_session_id: Mapped[str | None] = mapped_column(String(128), index=True)
    alipay_trade_no: Mapped[str | None] = mapped_column(String(64), index=True)  # 支付宝交易号
    alipay_buyer_logon_id: Mapped[str | None] = mapped_column(String(160))  # 买家支付宝账号
    alipay_buyer_user_id: Mapped[str | None] = mapped_column(String(32))  # 买家支付宝用户ID
    bank_receipt_url: Mapped[str | None] = mapped_column(String(700))  # 银行转账凭证URL
    bank_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # 银行转账核实时间
    status: Mapped[str] = mapped_column(String(40), default="created")
    raw_response: Mapped[dict] = mapped_column(JSON, default=dict)


class PaymentEvent(Base, TimestampMixin, TenantOwnedMixin):
    """Immutable provider event receipt used for replay-safe settlement."""

    __tablename__ = "payment_events"
    __table_args__ = (
        Index("uq_payment_events_provider_event", "provider", "provider_event_id", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40))
    provider_event_id: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(120))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default="received")
    error_code: Mapped[str | None] = mapped_column(String(120))


class Invoice(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "invoices"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    invoice_no: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)  # 发票号码
    invoice_code: Mapped[str | None] = mapped_column(String(32))  # 发票代码
    title: Mapped[str] = mapped_column(String(240))  # 发票抬头（购买方名称）
    tax_number: Mapped[str] = mapped_column(String(64))  # 购买方纳税人识别号
    address_phone: Mapped[str | None] = mapped_column(String(300))  # 购买方地址电话
    bank_account: Mapped[str | None] = mapped_column(String(200))  # 购买方开户行及账号
    seller_name: Mapped[str] = mapped_column(String(240), default="")  # 销售方名称
    seller_tax_number: Mapped[str] = mapped_column(String(64), default="")  # 销售方纳税人识别号
    items_json: Mapped[dict] = mapped_column(
        JSON, default=list
    )  # 发票明细 [{"name":"","spec":"","unit":"","qty":1,"price":0,"amount":0,"tax_rate":0}]
    amount: Mapped[float] = mapped_column(Numeric(12, 2))  # 合计金额（不含税）
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 税额
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))  # 价税合计
    invoice_type: Mapped[str] = mapped_column(
        String(40), default="vat_normal"
    )  # vat_normal/vat_special
    pdf_path: Mapped[str | None] = mapped_column(String(700))  # 生成的PDF文件路径
    status: Mapped[str] = mapped_column(String(40), default="requested")  # requested/generated/sent


class AnalyticsEvent(Base, TenantOwnedMixin):
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_event_tenant_name_time", "tenant_id", "name", "occurred_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    session_id: Mapped[str | None] = mapped_column(String(120))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)


class Product(Base, TimestampMixin):
    """Unified Product SKU — single source of truth for pricing."""

    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(
        String(80), unique=True, index=True
    )  # POLICY_REPORT, POLICY_DIAGNOSIS, etc.
    name: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    product_type: Mapped[str] = mapped_column(String(40))  # report / diagnosis / plan / draft
    price: Mapped[float] = mapped_column(Numeric(12, 2))  # current selling price
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2))  # strikethrough price
    promotional_price: Mapped[float | None] = mapped_column(Numeric(12, 2))  # limited-time price
    entitlement_type: Mapped[str] = mapped_column(
        String(40), default="report"
    )  # report / diagnosis / plan
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(default=0)  # display order


class Entitlement(Base, TimestampMixin, TenantOwnedMixin):
    """Tracks what a tenant has purchased and can access."""

    __tablename__ = "entitlements"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(40))  # report / diagnosis / plan
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )  # link to specific report/opportunity
    status: Mapped[str] = mapped_column(String(40), default="active")  # active / revoked / expired


class Agent(Base, TimestampMixin):
    """Versioned platform Agent definition with machine-readable contracts."""

    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("key", "version", name="uq_agent_key_version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="inactive")
    input_schema_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_schema_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Workflow(Base, TimestampMixin):
    """Versioned workflow definition executed by the Agent Harness."""

    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("key", "version", name="uq_workflow_key_version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="active")
    definition_json: Mapped[dict] = mapped_column(JSON, default=dict)


class WorkflowRun(Base, TimestampMixin, TenantOwnedMixin):
    """Tenant-owned execution of one immutable Workflow definition."""

    __tablename__ = "workflow_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    current_step: Mapped[str | None] = mapped_column(String(40))
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(14, 6), default=0)
    latency_ms: Mapped[int | None]
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(120))


class AgentRun(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_claimable", "status", "next_attempt_at", "lease_expires_at"),
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), index=True
    )
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    agent_name: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="running")
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    total_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(14, 6), default=0)
    latency_ms: Mapped[int | None]
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_json: Mapped[dict] = mapped_column(JSON, default=dict)
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=2)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    lease_owner: Mapped[str | None] = mapped_column(String(160))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentStep(Base, TenantOwnedMixin):
    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("agent_run_id", "sequence", name="uq_agent_step_sequence"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT")
    )
    sequence: Mapped[int]
    step_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="queued")
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_json: Mapped[dict] = mapped_column(JSON, default=dict)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(14, 6), default=0)
    latency_ms: Mapped[int | None]
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(120))


class ToolCall(Base, TenantOwnedMixin):
    __tablename__ = "tool_calls"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    agent_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_steps.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(160))
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="running")
    arguments_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int | None]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(120))


class AgentRunError(Base, TenantOwnedMixin):
    __tablename__ = "agent_run_errors"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    agent_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_steps.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))
    safe_message: Mapped[str] = mapped_column(String(500))
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AgentRetry(Base, TenantOwnedMixin):
    __tablename__ = "agent_retries"
    __table_args__ = (
        UniqueConstraint("agent_run_id", "retry_number", name="uq_agent_retry_number"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    retry_number: Mapped[int]
    reason_code: Mapped[str] = mapped_column(String(120))
    error_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Artifact(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint(
            "agent_run_id", "artifact_type", "version", name="uq_artifact_run_type_version"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(40), default="generated")
    mime_type: Mapped[str | None] = mapped_column(String(160))
    object_key: Mapped[str | None] = mapped_column(String(700))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLog(Base, TenantOwnedMixin):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(120))
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(80))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class Task(Base, TimestampMixin, TenantOwnedMixin):
    """Outcome-based Agent Task — core business object."""

    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_scans.id", ondelete="SET NULL"), index=True
    )
    task_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    requirements: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    agent_type: Mapped[str | None] = mapped_column(String(80))
    workflow_version: Mapped[str] = mapped_column(String(20), default="v1")
    model_provider: Mapped[str | None] = mapped_column(String(40))
    model_name: Mapped[str | None] = mapped_column(String(120))
    estimated_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    final_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    payment_status: Mapped[str] = mapped_column(String(40), default="unpaid")
    review_status: Mapped[str | None] = mapped_column(String(40))
    delivery_status: Mapped[str | None] = mapped_column(String(40))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress: Mapped[int] = mapped_column(default=0)
    current_stage: Mapped[str | None] = mapped_column(String(200))


class Deliverable(Base, TimestampMixin, TenantOwnedMixin):
    """Formal output artifact produced by an Agent task."""

    __tablename__ = "deliverables"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deliverable_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(500))
    content_json: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    content_markdown: Mapped[str | None] = mapped_column(Text)
    file_url: Mapped[str | None] = mapped_column(String(700))
    pdf_url: Mapped[str | None] = mapped_column(String(700))
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(40), default="generated")
    quality_score: Mapped[int | None] = mapped_column()
    evidence_score: Mapped[int | None] = mapped_column()
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RevisionRequest(Base, TenantOwnedMixin):
    """User-requested modification to a deliverable."""

    __tablename__ = "revision_requests"
    __table_args__ = (
        Index("ix_rev_req_task_id", "task_id"),
        Index("ix_rev_req_tenant_id", "tenant_id"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )
    deliverable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliverables.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    request: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    response: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
