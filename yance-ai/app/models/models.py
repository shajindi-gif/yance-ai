import enum
import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
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


class Company(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "companies"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(240))
    unified_credit_code: Mapped[str | None] = mapped_column(String(64))
    province: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(80))
    industry: Mapped[str | None] = mapped_column(String(160))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


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


class Policy(Base, TimestampMixin):
    """Global Policy Knowledge Base — platform-level, shared by all tenants."""
    __tablename__ = "policies"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(500))
    issuing_authority: Mapped[str | None] = mapped_column(String(240))  # 发文机关
    level: Mapped[str | None] = mapped_column(String(40))  # national/provincial/municipal/district
    province: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(80))
    industry: Mapped[str | None] = mapped_column(String(160))
    policy_type: Mapped[str | None] = mapped_column(String(80))  # subsidy/tax_break/qualification
    source_url: Mapped[str | None] = mapped_column(String(1000))
    jurisdiction: Mapped[str | None] = mapped_column(String(160))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content: Mapped[str | None] = mapped_column(Text)
    original_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(160))
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    support_amount: Mapped[str | None] = mapped_column(String(120))  # e.g. "最高500万"
    support_type: Mapped[str | None] = mapped_column(String(120))    # 资金补贴/税收优惠/资质认定
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    status: Mapped[str] = mapped_column(String(40), default="draft")


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


class Opportunity(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "opportunities"
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


class Order(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    product_code: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
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
    alipay_trade_no: Mapped[str | None] = mapped_column(String(64), index=True)    # 支付宝交易号
    alipay_buyer_logon_id: Mapped[str | None] = mapped_column(String(160))         # 买家支付宝账号
    alipay_buyer_user_id: Mapped[str | None] = mapped_column(String(32))           # 买家支付宝用户ID
    bank_receipt_url: Mapped[str | None] = mapped_column(String(700))              # 银行转账凭证URL
    bank_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 银行转账核实时间
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
    invoice_code: Mapped[str | None] = mapped_column(String(32))                         # 发票代码
    title: Mapped[str] = mapped_column(String(240))           # 发票抬头（购买方名称）
    tax_number: Mapped[str] = mapped_column(String(64))       # 购买方纳税人识别号
    address_phone: Mapped[str | None] = mapped_column(String(300))  # 购买方地址电话
    bank_account: Mapped[str | None] = mapped_column(String(200))    # 购买方开户行及账号
    seller_name: Mapped[str] = mapped_column(String(240), default="")   # 销售方名称
    seller_tax_number: Mapped[str] = mapped_column(String(64), default="")  # 销售方纳税人识别号
    items_json: Mapped[dict] = mapped_column(JSON, default=list)    # 发票明细 [{"name":"","spec":"","unit":"","qty":1,"price":0,"amount":0,"tax_rate":0}]
    amount: Mapped[float] = mapped_column(Numeric(12, 2))          # 合计金额（不含税）
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 税额
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))    # 价税合计
    invoice_type: Mapped[str] = mapped_column(String(40), default="vat_normal")  # vat_normal/vat_special
    pdf_path: Mapped[str | None] = mapped_column(String(700))      # 生成的PDF文件路径
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
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # POLICY_REPORT, POLICY_DIAGNOSIS, etc.
    name: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    product_type: Mapped[str] = mapped_column(String(40))  # report / diagnosis / plan / draft
    price: Mapped[float] = mapped_column(Numeric(12, 2))  # current selling price
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2))  # strikethrough price
    promotional_price: Mapped[float | None] = mapped_column(Numeric(12, 2))  # limited-time price
    entitlement_type: Mapped[str] = mapped_column(String(40), default="report")  # report / diagnosis / plan
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
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # link to specific report/opportunity
    status: Mapped[str] = mapped_column(String(40), default="active")  # active / revoked / expired


class AgentRun(Base, TenantOwnedMixin):
    __tablename__ = "agent_runs"
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    agent_name: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    latency_ms: Mapped[int | None]
    error_code: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


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
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"))
    task_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    requirements: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="draft")
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
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress: Mapped[int] = mapped_column(default=0)
    current_stage: Mapped[str | None] = mapped_column(String(200))


class Deliverable(Base, TimestampMixin, TenantOwnedMixin):
    """Formal output artifact produced by an Agent task."""
    __tablename__ = "deliverables"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deliverable_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(500))
    content_json: Mapped[dict | None] = mapped_column(JSON)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    deliverable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deliverables.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    request: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    response: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
