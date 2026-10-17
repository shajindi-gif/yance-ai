import enum
import uuid
from datetime import UTC, date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
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
    account_stage: Mapped[str] = mapped_column(String(40), default="unclassified", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    demo_dataset_key: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)


class DemoScenario(Base, TimestampMixin):
    """Platform-owned index over a complete, tenant-isolated synthetic workflow."""

    __tablename__ = "demo_scenarios"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_profile_versions.id", ondelete="CASCADE")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_scans.id", ondelete="CASCADE")
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE")
    )
    eligibility_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eligibility_results.id", ondelete="CASCADE")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE")
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_artifacts.id", ondelete="CASCADE")
    )
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(240))
    industry: Mapped[str] = mapped_column(String(160))
    persona: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text)
    next_best_action: Mapped[str] = mapped_column(Text)
    dataset_version: Mapped[str] = mapped_column(String(80), index=True)
    data_classification: Mapped[str] = mapped_column(String(40), default="synthetic")
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    display_order: Mapped[int] = mapped_column(default=0)


class User(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "users"
    __table_args__ = (Index("uq_users_tenant_email", "tenant_id", "email", unique=True),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.member)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


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
    __table_args__ = (UniqueConstraint("profile_id", "version", name="uq_company_profile_version"),)
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


class DocumentIngestionRun(Base, TimestampMixin, TenantOwnedMixin):
    """Durable, retryable execution record for one document ingestion attempt."""

    __tablename__ = "document_ingestion_runs"
    __table_args__ = (
        UniqueConstraint("document_id", "attempt", name="uq_document_ingestion_attempt"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    attempt: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    parser_version: Mapped[str] = mapped_column(String(80), default="document-parser-v1")
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(120))
    safe_message: Mapped[str | None] = mapped_column(String(500))
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DocumentContent(Base, TimestampMixin, TenantOwnedMixin):
    """Canonical bounded text projection produced by a verified parser."""

    __tablename__ = "document_contents"
    __table_args__ = (UniqueConstraint("document_id", name="uq_document_content_document"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    parser: Mapped[str] = mapped_column(String(80))
    parser_version: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64), index=True)
    character_count: Mapped[int]
    page_count: Mapped[int | None]
    language: Mapped[str | None] = mapped_column(String(40))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DocumentChunk(Base, TimestampMixin, TenantOwnedMixin):
    """Source-locatable chunks for company document retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "sequence", name="uq_document_chunk_sequence"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    character_start: Mapped[int]
    character_end: Mapped[int]
    token_estimate: Mapped[int]
    locator_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))


class DocumentFactCandidate(Base, TimestampMixin, TenantOwnedMixin):
    """A review-required company fact grounded in an exact document excerpt."""

    __tablename__ = "document_fact_candidates"
    __table_args__ = (
        UniqueConstraint("document_id", "candidate_hash", name="uq_document_fact_candidate_hash"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    field_key: Mapped[str] = mapped_column(String(120), index=True)
    value_json: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3))
    evidence_excerpt: Mapped[str] = mapped_column(Text)
    source_locator_json: Mapped[dict] = mapped_column(JSON, default=dict)
    extraction_method: Mapped[str] = mapped_column(String(80), default="deterministic")
    extraction_version: Mapped[str] = mapped_column(String(80), default="company-intelligence-v1")
    candidate_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default="pending_review", index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
    # Funding OS: structured funding facts (parsed deterministically or curated;
    # never fabricated — leave NULL when the official document does not state it)
    funding_type: Mapped[str | None] = mapped_column(
        String(40), index=True
    )  # grant/tax_incentive/loan_discount/voucher/talent/competition/equity/service
    funding_amount_min: Mapped[float | None] = mapped_column(Numeric(14, 2))  # 万元
    funding_amount_max: Mapped[float | None] = mapped_column(Numeric(14, 2))  # 万元
    funding_ratio: Mapped[float | None] = mapped_column(Numeric(5, 2))  # % of eligible spend
    funding_currency: Mapped[str | None] = mapped_column(String(8), default="CNY")
    applicant_type: Mapped[str | None] = mapped_column(String(120))
    company_stage: Mapped[str | None] = mapped_column(String(160))
    technology: Mapped[str | None] = mapped_column(String(240))
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


class PolicyVersion(Base, TimestampMixin):
    """Immutable, checksum-addressed policy source snapshot."""

    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("policy_id", "version", name="uq_policy_version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    version: Mapped[int]
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    issuer: Mapped[str | None] = mapped_column(String(240))
    region: Mapped[str | None] = mapped_column(String(160))
    industry: Mapped[str | None] = mapped_column(String(160))
    policy_type: Mapped[str | None] = mapped_column(String(80))
    publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_name: Mapped[str | None] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="published", index=True)


class PolicyChunk(Base, TimestampMixin):
    """Paragraph-level retrieval unit with an exact span in a policy version."""

    __tablename__ = "policy_chunks"
    __table_args__ = (
        UniqueConstraint("policy_version_id", "chunk_index", name="uq_policy_chunk_index"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    chunk_index: Mapped[int]
    article: Mapped[str | None] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    char_start: Mapped[int]
    char_end: Mapped[int]
    content_sha256: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))


class EligibilityRule(Base, TimestampMixin):
    """Typed deterministic condition pinned to one immutable policy version."""

    __tablename__ = "eligibility_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(300))
    fact_key: Mapped[str] = mapped_column(String(120))
    operator: Mapped[str] = mapped_column(String(40))
    expected_json: Mapped[dict] = mapped_column(JSON)
    is_hard_gate: Mapped[bool] = mapped_column(Boolean, default=True)
    source_quote: Mapped[str] = mapped_column(Text)
    article: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(40), default="active")


class RequiredMaterial(Base, TimestampMixin):
    __tablename__ = "required_materials"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    is_hard_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    source_quote: Mapped[str] = mapped_column(Text)
    article: Mapped[str | None] = mapped_column(String(160))


class PolicyBenefit(Base, TimestampMixin):
    __tablename__ = "policy_benefits"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=True
    )
    benefit_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    amount_text: Mapped[str | None] = mapped_column(String(160))
    source_quote: Mapped[str] = mapped_column(Text)
    article: Mapped[str | None] = mapped_column(String(160))


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
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="RESTRICT"), index=True
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


class EligibilityResult(Base, TimestampMixin, TenantOwnedMixin):
    """Auditable four-state decision for one opportunity and profile snapshot."""

    __tablename__ = "eligibility_results"
    __table_args__ = (UniqueConstraint("opportunity_id", name="uq_eligibility_opportunity"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="SET NULL"), index=True
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_profile_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0)
    summary: Mapped[str] = mapped_column(Text)
    criteria_json: Mapped[list] = mapped_column(JSON, default=list)
    missing_information_json: Mapped[list] = mapped_column(JSON, default=list)
    engine_version: Mapped[str] = mapped_column(String(80), default="deterministic-v1")
    review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Evidence(Base, TimestampMixin, TenantOwnedMixin):
    """Exact source citation used by an eligibility decision."""

    __tablename__ = "evidence"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    eligibility_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eligibility_results.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="RESTRICT"), index=True
    )
    policy_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_chunks.id", ondelete="RESTRICT"), index=True
    )
    eligibility_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eligibility_rules.id", ondelete="SET NULL")
    )
    source_title: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    issuer: Mapped[str | None] = mapped_column(String(240))
    article: Mapped[str | None] = mapped_column(String(160))
    quote: Mapped[str] = mapped_column(Text)
    quote_start: Mapped[int]
    quote_end: Mapped[int]
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=1)
    verifier: Mapped[str] = mapped_column(String(80), default="exact_span_v1")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


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


class ApplicationDocumentLink(Base, TimestampMixin, TenantOwnedMixin):
    """Tenant-scoped association between a case, a company document and an optional requirement."""

    __tablename__ = "application_document_links"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "document_id",
            "requirement_id",
            name="uq_application_document_requirement",
            postgresql_nulls_not_distinct=True,
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_requirements.id", ondelete="SET NULL"),
        index=True,
    )
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(40), default="linked")


class ApplicationArtifact(Base, TimestampMixin, TenantOwnedMixin):
    """Immutable source-pinned Application draft; edits create a new version."""

    __tablename__ = "application_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "artifact_type", "version", name="uq_application_artifact_version"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    artifact_type: Mapped[str] = mapped_column(String(80), default="application_brief")
    title: Mapped[str] = mapped_column(String(500))
    version: Mapped[int]
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    generation_method: Mapped[str] = mapped_column(String(120), default="deterministic-evidence-v1")
    content_json: Mapped[dict] = mapped_column(JSON)
    source_snapshot_json: Mapped[dict] = mapped_column(JSON)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)


class ApplicationComment(Base, TenantOwnedMixin):
    __tablename__ = "application_comments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


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
        UniqueConstraint("tenant_id", "event_key", name="uq_analytics_event_tenant_key"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    session_id: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(40), default="server", index=True)
    event_key: Mapped[str | None] = mapped_column(String(240))
    request_id: Mapped[str | None] = mapped_column(String(120))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)


class Feedback(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "feedback"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[str] = mapped_column(String(80), default="product")
    message: Mapped[str] = mapped_column(Text)
    route: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)


class EvalDataset(Base, TimestampMixin):
    """Global evaluation dataset identity; content lives in immutable versions."""

    __tablename__ = "eval_datasets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240))
    eval_type: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    data_classification: Mapped[str] = mapped_column(String(80), default="synthetic")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class EvalDatasetVersion(Base):
    __tablename__ = "eval_dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_eval_dataset_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_datasets.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[str] = mapped_column(String(80))
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    case_count: Mapped[int]
    target_key: Mapped[str] = mapped_column(String(160))
    target_version: Mapped[str] = mapped_column(String(80))
    scorer_version: Mapped[str] = mapped_column(String(80))
    review_status: Mapped[str] = mapped_column(String(40), default="unreviewed", index=True)
    card_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class EvalCase(Base):
    __tablename__ = "eval_cases"
    __table_args__ = (
        UniqueConstraint("dataset_version_id", "case_id", name="uq_eval_case_version_key"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_dataset_versions.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[str] = mapped_column(String(160))
    eval_type: Mapped[str] = mapped_column(String(80), index=True)
    question: Mapped[str] = mapped_column(Text)
    input_json: Mapped[dict] = mapped_column(JSON)
    ground_truth_json: Mapped[dict] = mapped_column(JSON)
    expected_evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    tags_json: Mapped[list] = mapped_column(JSON, default=list)
    risk_tier: Mapped[str] = mapped_column(String(40), index=True)
    reference_date: Mapped[date | None] = mapped_column(Date)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)


class EvalRun(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "eval_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_dataset_versions.id", ondelete="RESTRICT"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    eval_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    target_key: Mapped[str] = mapped_column(String(160))
    target_version: Mapped[str] = mapped_column(String(80))
    scorer_version: Mapped[str] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(160))
    prompt_version: Mapped[str | None] = mapped_column(String(120))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    requested_cases: Mapped[int] = mapped_column(default=0)
    completed_cases: Mapped[int] = mapped_column(default=0)
    passed_cases: Mapped[int] = mapped_column(default=0)
    error_cases: Mapped[int] = mapped_column(default=0)
    total_latency_ms: Mapped[int] = mapped_column(default=0)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(14, 6), default=0)
    release_gate_passed: Mapped[bool | None] = mapped_column(Boolean)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Evaluation(Base, TenantOwnedMixin):
    """One executed case result. Errors remain first-class denominator rows."""

    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("eval_run_id", "eval_case_id", name="uq_evaluation_run_case"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    eval_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True
    )
    eval_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_cases.id", ondelete="RESTRICT"), index=True
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), index=True)
    model_answer_json: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_score: Mapped[float | None] = mapped_column(Numeric(6, 5))
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    hallucination_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    error_types_json: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(14, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class EvaluationDimensionScore(Base, TenantOwnedMixin):
    __tablename__ = "evaluation_dimension_scores"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "dimension", name="uq_evaluation_dimension"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True
    )
    dimension: Mapped[str] = mapped_column(String(80), index=True)
    score: Mapped[float | None] = mapped_column(Numeric(6, 5))
    is_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    scorer: Mapped[str] = mapped_column(String(160))
    scorer_version: Mapped[str] = mapped_column(String(80))
    rationale: Mapped[str] = mapped_column(Text)


class EvaluationEvidence(Base, TenantOwnedMixin):
    __tablename__ = "evaluation_evidence"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True
    )
    expectation: Mapped[str] = mapped_column(Text)
    observed: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    passed: Mapped[bool] = mapped_column(Boolean)


class EvaluationError(Base, TenantOwnedMixin):
    __tablename__ = "evaluation_errors"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    eval_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[str] = mapped_column(String(160), index=True)
    code: Mapped[str] = mapped_column(String(120), index=True)
    error_type: Mapped[str] = mapped_column(String(120), index=True)
    safe_message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Plan(Base, TimestampMixin):
    """Version-independent SaaS package; limits are server-owned configuration."""

    __tablename__ = "plans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    tier: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    sales_motion: Mapped[str] = mapped_column(String(40), default="self_serve")
    limits_json: Mapped[dict] = mapped_column(JSON, default=dict)
    features_json: Mapped[list] = mapped_column(JSON, default=list)


class PriceVersion(Base, TimestampMixin):
    """Immutable commercial price attached to a Plan."""

    __tablename__ = "price_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version", name="uq_price_version_plan"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), index=True
    )
    version: Mapped[int]
    currency: Mapped[str] = mapped_column(String(8))
    unit_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    billing_interval: Mapped[str] = mapped_column(String(20), default="month")
    provider: Mapped[str | None] = mapped_column(String(40))
    provider_price_id: Mapped[str | None] = mapped_column(String(160), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), index=True
    )
    price_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_versions.id", ondelete="RESTRICT"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40), default="internal")
    provider_customer_id: Mapped[str | None] = mapped_column(String(160), index=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(160), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grace_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class SubscriptionItem(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "subscription_items"
    __table_args__ = (
        UniqueConstraint("subscription_id", "meter_key", name="uq_subscription_item_meter"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    meter_key: Mapped[str] = mapped_column(String(80), index=True)
    quantity: Mapped[int] = mapped_column(default=1)


class UsageMeter(Base, TimestampMixin):
    __tablename__ = "usage_meters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    unit: Mapped[str] = mapped_column(String(40))
    aggregation: Mapped[str] = mapped_column(String(40), default="sum")
    source: Mapped[str] = mapped_column(String(80))
    reset_period: Mapped[str] = mapped_column(String(20), default="subscription")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class UsageRecord(Base, TenantOwnedMixin):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_usage_record_tenant_key"),
        Index("ix_usage_records_meter_period", "tenant_id", "meter_key", "occurred_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True
    )
    meter_key: Mapped[str] = mapped_column(String(80), index=True)
    quantity: Mapped[int]
    idempotency_key: Mapped[str] = mapped_column(String(200))
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(80), default="server")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class UsageBudget(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "usage_budgets"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "scope_type", "scope_id", "meter_key", name="uq_usage_budget_scope"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[str] = mapped_column(String(40), index=True)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    meter_key: Mapped[str] = mapped_column(String(80), index=True)
    hard_limit: Mapped[int]
    warning_threshold: Mapped[int | None]
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ApiKey(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("tenant_id", "prefix", name="uq_api_key_tenant_prefix"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(160))
    prefix: Mapped[str] = mapped_column(String(24), index=True)
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes_json: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class RetentionPolicy(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "retention_policies"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_retention_policy_tenant"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_days: Mapped[int] = mapped_column(default=365)
    agent_trace_days: Mapped[int] = mapped_column(default=180)
    analytics_days: Mapped[int] = mapped_column(default=365)
    audit_days: Mapped[int] = mapped_column(default=730)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    legal_hold_reason: Mapped[str | None] = mapped_column(String(500))
    configured_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class ExportJob(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "export_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    format: Mapped[str] = mapped_column(String(20), default="json")
    scope: Mapped[str] = mapped_column(String(40), default="workspace")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    record_counts_json: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(120))


class DeletionRequest(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "deletion_requests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(40), default="scheduled", index=True)
    reason: Mapped[str | None] = mapped_column(String(500))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocker_json: Mapped[list] = mapped_column(JSON, default=list)


class FeatureFlag(Base, TimestampMixin):
    __tablename__ = "feature_flags"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    enabled_by_default: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(40), default="active")


class TenantFeatureFlag(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "tenant_feature_flags"
    __table_args__ = (UniqueConstraint("tenant_id", "feature_flag_id", name="uq_tenant_flag"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feature_flags.id", ondelete="CASCADE"), index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean)


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
    request_id: Mapped[str | None] = mapped_column(String(120), index=True)
    result: Mapped[str] = mapped_column(String(40), default="success")
    reason: Mapped[str | None] = mapped_column(String(500))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    entry_hash: Mapped[str | None] = mapped_column(String(64), index=True)


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


class Notification(Base, TenantOwnedMixin):
    """In-app notification (deadline reminders, pipeline events). Deduped per tenant."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dedup_key", name="uq_notification_tenant_key"),
        Index("ix_notification_tenant_created", "tenant_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40), index=True)  # deadline/pipeline/agent/system
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info/warning/critical
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    dedup_key: Mapped[str] = mapped_column(String(200))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Milestone(Base, TimestampMixin, TenantOwnedMixin):
    """Deadline-driven task or post-award project checkpoint under an application."""

    __tablename__ = "milestones"
    __table_args__ = (
        Index("ix_milestone_tenant_due", "tenant_id", "due_at"),
        Index("ix_milestone_application", "application_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(40), default="preparation")  # preparation/acceptance
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="todo", index=True)  # todo/doing/done/blocked
    completion_note: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailCode(Base):
    """One-time email verification codes for passwordless login/registration.

    Pre-tenant table: codes exist before the user belongs to any workspace,
    so this deliberately has no tenant_id. Codes are stored only as SHA-256
    hashes; rate limiting is enforced against this table (DB-backed, safe
    across the 4 uvicorn workers, unlike in-memory counters).
    """

    __tablename__ = "email_codes"
    __table_args__ = (
        Index("ix_email_code_email_created", "email", "created_at"),
        Index("ix_email_code_ip_created", "ip_address", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(20), default="login")  # login (register folded in)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuthRateLimit(Base):
    """Shared, DB-backed fixed-window counters for auth endpoints.

    Replaces the in-memory _register_rate dict, which counted independently in
    each of the 4 uvicorn workers (effective threshold x4, reset on restart).
    Key format: "<action>:<client-ip>", e.g. "register:1.2.3.4".
    """

    __tablename__ = "auth_rate_limit"
    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    count: Mapped[int] = mapped_column(Integer, default=1)
