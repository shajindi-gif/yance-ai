from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.models import UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BootstrapRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=160)
    tenant_slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")
    owner_email: EmailStr
    owner_name: str = Field(min_length=2, max_length=160)
    owner_password: str = Field(min_length=12, max_length=128)


class RegisterRequest(BaseModel):
    """Public self-service registration: tenant + owner + default company."""

    company_name: str = Field(min_length=2, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    province: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    owner_email: EmailStr
    owner_name: str = Field(min_length=2, max_length=160)
    owner_password: str = Field(min_length=12, max_length=128)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.member


class UserOut(ORMModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_platform_admin: bool


class TenantOut(ORMModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    account_stage: str


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    unified_credit_code: str | None = None
    province: str | None = None
    city: str | None = None
    industry: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CompanyOut(CompanyCreate, ORMModel):
    id: UUID
    tenant_id: UUID
    created_at: datetime


class CompanyProfileData(BaseModel):
    """Validated draft facts; published versions are immutable copies of this contract."""

    model_config = ConfigDict(extra="forbid")

    industry: str | None = Field(default=None, max_length=160)
    province: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)
    registered_address: str | None = Field(default=None, max_length=500)
    founded_date: date | None = None
    company_scale: str | None = Field(default=None, max_length=80)
    employee_count: int | None = Field(default=None, ge=0, le=10_000_000)
    revenue_stage: str | None = Field(default=None, max_length=120)
    annual_revenue: float | None = Field(default=None, ge=0)
    funding_stage: str | None = Field(default=None, max_length=120)
    high_tech_status: str | None = Field(default=None, max_length=120)
    tech_sme_status: str | None = Field(default=None, max_length=120)
    specialized_sme_status: str | None = Field(default=None, max_length=120)
    intellectual_property: list[str] = Field(default_factory=list, max_length=200)
    core_products: list[str] = Field(default_factory=list, max_length=100)
    rd_summary: str | None = Field(default=None, max_length=4000)
    rd_expense_ratio: float | None = Field(default=None, ge=0, le=100)
    talent_summary: str | None = Field(default=None, max_length=4000)
    projects: list[str] = Field(default_factory=list, max_length=100)
    current_needs: list[str] = Field(default_factory=list, max_length=100)


class CompanyProfileOut(ORMModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID
    status: str
    draft_json: dict[str, Any]
    completeness_score: int
    published_version: int | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CompanyProfileVersionOut(ORMModel):
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    company_id: UUID
    version: int
    snapshot_json: dict[str, Any]
    completeness_score: int
    created_by: UUID | None
    published_at: datetime


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    company_id: UUID | None = None
    size_bytes: int = Field(gt=0)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class DocumentOut(ORMModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID | None
    filename: str
    content_type: str
    object_key: str
    status: str
    size_bytes: int | None
    source_type: str
    ingestion_status: str
    ingestion_error: str | None
    ingested_at: datetime | None
    created_at: datetime


class PresignedUploadOut(BaseModel):
    document: DocumentOut
    upload_url: str
    method: str = "PUT"
    expires_in: int
    required_headers: dict[str, str]


class DocumentComplete(BaseModel):
    checksum_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class PolicyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    issuing_authority: str | None = Field(default=None, max_length=240)
    level: str | None = Field(default=None, max_length=40)
    province: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    industry: str | None = Field(default=None, max_length=160)
    policy_type: str | None = Field(default=None, max_length=80)
    source_url: str | None = None
    jurisdiction: str | None = None
    published_at: datetime | None = None
    effective_at: datetime | None = None
    deadline: datetime | None = None
    source: str | None = Field(default=None, max_length=160)
    support_amount: str | None = Field(default=None, max_length=120)
    support_type: str | None = Field(default=None, max_length=120)
    content: str | None = None
    status: str = "draft"


class PolicyOut(PolicyCreate, ORMModel):
    id: UUID
    tenant_id: UUID | None
    created_at: datetime
    embedding: list[float] | None = None


class PolicyRuleCreate(BaseModel):
    policy_id: UUID
    name: str = Field(min_length=2, max_length=300)
    rule_type: str = Field(min_length=2, max_length=80)
    rule_json: dict[str, Any] = Field(default_factory=dict)
    explanation: str | None = None


class PolicyRuleOut(PolicyRuleCreate, ORMModel):
    id: UUID
    tenant_id: UUID
    created_at: datetime


class EligibilityRuleCreate(BaseModel):
    policy_id: UUID
    policy_version_id: UUID | None = None
    name: str = Field(min_length=2, max_length=300)
    fact_key: str = Field(min_length=1, max_length=120)
    operator: Literal["eq", "in", "contains", "gte", "lte", "exists"]
    expected_json: dict[str, Any] = Field(default_factory=dict)
    is_hard_gate: bool = True
    source_quote: str = Field(min_length=1)
    article: str | None = Field(default=None, max_length=160)


class EligibilityRuleOut(EligibilityRuleCreate, ORMModel):
    id: UUID
    tenant_id: UUID | None
    policy_version_id: UUID
    status: str
    created_at: datetime


class RequiredMaterialCreate(BaseModel):
    policy_id: UUID
    policy_version_id: UUID | None = None
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    is_hard_gate: bool = False
    source_quote: str = Field(min_length=1)
    article: str | None = Field(default=None, max_length=160)


class RequiredMaterialOut(RequiredMaterialCreate, ORMModel):
    id: UUID
    tenant_id: UUID | None
    policy_version_id: UUID
    created_at: datetime


class PolicyBenefitCreate(BaseModel):
    policy_id: UUID
    policy_version_id: UUID | None = None
    benefit_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1)
    amount_text: str | None = Field(default=None, max_length=160)
    source_quote: str = Field(min_length=1)
    article: str | None = Field(default=None, max_length=160)


class PolicyBenefitOut(PolicyBenefitCreate, ORMModel):
    id: UUID
    tenant_id: UUID | None
    policy_version_id: UUID
    created_at: datetime


class OpportunityCreate(BaseModel):
    company_id: UUID
    policy_id: UUID | None = None
    title: str = Field(min_length=2, max_length=500)
    score: float | None = Field(default=None, ge=0, le=1)
    status: str = "identified"
    evidence_json: dict[str, Any] = Field(default_factory=dict)


class OpportunityOut(OpportunityCreate, ORMModel):
    id: UUID
    tenant_id: UUID
    scan_id: UUID | None
    profile_version_id: UUID | None
    policy_version_id: UUID | None
    policy_snapshot_json: dict[str, Any]
    eligibility_status: Literal[
        "ELIGIBLE", "POTENTIALLY_ELIGIBLE", "NOT_ELIGIBLE", "NEED_MORE_INFORMATION"
    ]
    eligibility_confidence: float | None
    created_at: datetime


class ApplicationCreate(BaseModel):
    company_id: UUID
    opportunity_id: UUID | None = None
    title: str = Field(min_length=2, max_length=500)
    status: str = "draft"
    form_data: dict[str, Any] = Field(default_factory=dict)


class ApplicationOut(ApplicationCreate, ORMModel):
    id: UUID
    tenant_id: UUID
    owner_user_id: UUID | None
    due_at: datetime | None
    progress: int
    review_status: str
    created_at: datetime


class ApplicationDocumentLinkCreate(BaseModel):
    document_id: UUID
    requirement_id: UUID | None = None


class ApplicationCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class ApplicationAgentAction(BaseModel):
    action: Literal["ask", "generate", "check", "fix", "explain"]
    question: str | None = Field(default=None, max_length=1000)
    instruction: str | None = Field(default=None, max_length=2000)


class ApplicationArtifactEdit(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    executive_summary: str | None = Field(default=None, min_length=2, max_length=5000)

    @model_validator(mode="after")
    def require_change(self) -> "ApplicationArtifactEdit":
        if self.title is None and self.executive_summary is None:
            raise ValueError("At least one editable field is required")
        return self


class ApplicationArtifactReview(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=2000)


class OrderCreate(BaseModel):
    product_code: str
    resource_id: UUID | None = None


class PaymentCreate(BaseModel):
    order_id: UUID
    provider: str = "alipay"
    amount: float = Field(gt=0)


class InvoiceCreate(BaseModel):
    order_id: UUID
    title: str = Field(min_length=2, max_length=240, description="发票抬头（购买方名称）")
    tax_number: str = Field(min_length=15, max_length=64, description="购买方纳税人识别号")
    address_phone: str | None = None
    bank_account: str | None = None
    seller_name: str = ""
    seller_tax_number: str = ""
    items: list[dict] | None = None  # 发票明细，为空则自动从订单生成
    invoice_type: str = "vat_normal"  # vat_normal / vat_special / vat_electronic


class InvoiceOut(ORMModel):
    id: UUID
    order_id: UUID
    tenant_id: UUID
    invoice_no: str | None = None
    invoice_code: str | None = None
    title: str
    tax_number: str
    amount: float
    tax_amount: float
    total_amount: float
    invoice_type: str
    pdf_path: str | None = None
    status: str
    created_at: datetime


class CommerceOut(ORMModel):
    id: UUID
    tenant_id: UUID
    status: str
    amount: float | None = None
    created_at: datetime


class OrderOut(ORMModel):
    id: UUID
    tenant_id: UUID
    order_no: str
    product_code: str
    amount: float
    currency: str
    resource_type: str | None
    resource_id: UUID | None
    status: str
    created_at: datetime


class AnalyticsEventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    session_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class FeedbackCreate(BaseModel):
    category: Literal["product", "data", "policy", "billing", "support"] = "product"
    message: str = Field(min_length=2, max_length=5000)
    route: str | None = Field(default=None, max_length=500)


class FeedbackStatusUpdate(BaseModel):
    status: Literal["open", "reviewing", "resolved", "dismissed"]


class TenantAccountStageUpdate(BaseModel):
    account_stage: Literal["unclassified", "poc", "customer", "churned", "internal"]


class EvalRunRequest(BaseModel):
    eval_type: Literal[
        "all",
        "policy_retrieval_eval",
        "eligibility_eval",
        "citation_eval",
        "hallucination_eval",
        "document_generation_eval",
    ] = "all"


class AgentRunCreate(BaseModel):
    agent_name: str
    provider: str
    model: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AgentRunFinish(BaseModel):
    status: str = "completed"
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    error_code: str | None = None
