// Yance.ai API Client
// Connects the Next.js frontend to the FastAPI backend

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  account_stage: string;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  role: string;
  is_active: boolean;
  is_platform_admin: boolean;
}

export interface AdminTotals {
  total_users: number;
  active_users_30d: number;
  organizations: number;
  companies: number;
  policy_scans: number;
  applications: number;
  reports_generated: number;
  agent_runs: number;
  successful_runs: number;
  failed_runs: number;
  documents_generated: number;
  poc_accounts: number;
  paying_customers: number;
  llm_cost_usd: number;
  cost_per_run_usd: number | null;
}

export interface AdminFunnelStep {
  event: string;
  label: string;
  organizations: number;
  conversion_from_previous: number | null;
}

export interface AgentTrendPoint {
  date: string;
  runs: number;
  successful: number;
  failed: number;
  cost_usd: number;
}

export interface AdminSystemHealth {
  checked_at: string;
  database: string;
  agent_queue: { queued: number; running: number; stale_running: number; failed_24h: number };
  workflow_runs: { running: number; failed_24h: number };
  documents: { pending_ingestion: number; failed_ingestion: number };
  errors_24h: number;
  open_feedback: number;
  api_latency_history: { available: boolean; reason: string };
}

export interface AdminOverview {
  generated_at: string;
  totals: AdminTotals;
  revenue_by_currency: Array<{ currency: string; amount: number }>;
  funnel: AdminFunnelStep[];
  agent_trend_30d: AgentTrendPoint[];
  system_health: AdminSystemHealth;
  resources: Record<string, number>;
  capabilities: Record<string, { available: boolean; message: string }>;
}

export interface InvestorMetrics extends Omit<AdminOverview, 'system_health' | 'resources' | 'capabilities'> {
  scope: string;
  window: Record<string, string>;
  definitions: Record<string, string>;
  availability: Record<string, boolean>;
}

export interface AdminResourcePage {
  total: number;
  limit: number;
  offset: number;
  items: Array<Record<string, unknown>>;
  available?: boolean;
  message?: string;
}

export type EvalType =
  | 'policy_retrieval_eval'
  | 'eligibility_eval'
  | 'citation_eval'
  | 'hallucination_eval'
  | 'document_generation_eval';

export interface EvalRunSummary {
  id: string;
  batch_id: string;
  eval_type: EvalType;
  status: string;
  target_key: string;
  target_version: string;
  scorer_version: string;
  model: string | null;
  requested_cases: number;
  completed_cases: number;
  passed_cases: number;
  error_cases: number;
  total_latency_ms: number;
  total_cost_usd: number;
  release_gate_passed: boolean | null;
  created_at: string;
  finished_at: string | null;
}

export interface EvaluationOverview {
  available: boolean;
  message: string | null;
  generated_at: string;
  scope: string;
  cards: {
    accuracy: number | null;
    citation_accuracy: number | null;
    hallucination_rate: number | null;
    pass_rate: number | null;
    average_latency_ms: number | null;
    average_cost_usd: number | null;
  };
  counts: { requested: number; completed: number; passed: number; errors: number };
  dimensions: Array<{ dimension: string; score: number | null; sample_size: number }>;
  runs: Array<EvalRunSummary & {
    dataset: string;
    dataset_key: string;
    dataset_version: string;
    review_status: string;
    data_classification: string;
  }>;
  investor_quality_eligible: boolean;
}

export interface EvalRunDetail {
  run: EvalRunSummary;
  dataset: {
    key: string;
    name: string;
    description: string;
    version: string;
    content_sha256: string;
    review_status: string;
    data_classification: string;
    case_count: number;
    card: Record<string, unknown>;
  };
  cases: Array<{
    case_id: string;
    question: string;
    risk_tier: string;
    tags: string[];
    ground_truth: Record<string, unknown>;
    model_answer: Record<string, unknown>;
    status: string;
    overall_score: number | null;
    passed: boolean;
    latency_ms: number;
    cost_usd: number;
    error_types: string[];
    dimensions: Array<{
      dimension: string;
      score: number | null;
      is_applicable: boolean;
      scorer: string;
      scorer_version: string;
      rationale: string;
    }>;
    evidence: Array<{
      expectation: string;
      observed: string;
      source_reference: string | null;
      passed: boolean;
    }>;
    errors: Array<{ code: string; error_type: string; safe_message: string }>;
  }>;
}

export interface Company {
  id: string;
  tenant_id: string;
  name: string;
  unified_credit_code?: string;
  province?: string;
  city?: string;
  industry?: string;
  metadata_json?: Record<string, unknown>;
  created_at: string;
}

export interface Policy {
  id: string;
  tenant_id: string | null;
  title: string;
  source_url?: string;
  jurisdiction?: string;
  content: string;
  status: string;
  created_at: string;
}

export interface CompanyProfileData {
  industry: string | null;
  province: string | null;
  city: string | null;
  registered_address: string | null;
  founded_date: string | null;
  company_scale: string | null;
  employee_count: number | null;
  revenue_stage: string | null;
  annual_revenue: number | null;
  funding_stage: string | null;
  high_tech_status: string | null;
  tech_sme_status: string | null;
  specialized_sme_status: string | null;
  intellectual_property: string[];
  core_products: string[];
  rd_summary: string | null;
  rd_expense_ratio: number | null;
  talent_summary: string | null;
  projects: string[];
  current_needs: string[];
}

export interface CompanyProfile {
  id: string;
  tenant_id: string;
  company_id: string;
  status: string;
  draft_json: CompanyProfileData;
  completeness_score: number;
  published_version: number | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompanyProfileVersion {
  id: string;
  tenant_id: string;
  profile_id: string;
  company_id: string;
  version: number;
  snapshot_json: CompanyProfileData;
  completeness_score: number;
  created_by: string | null;
  published_at: string;
}

export interface DocumentRecord {
  id: string;
  tenant_id: string;
  company_id: string | null;
  filename: string;
  content_type: string;
  object_key: string;
  status: string;
  size_bytes: number | null;
  checksum_sha256: string | null;
  metadata_json: Record<string, unknown>;
  source_type: string;
  ingestion_status: string;
  ingestion_error: string | null;
  ingested_at: string | null;
  created_at: string;
}

export interface DocumentFactCandidate {
  id: string;
  document_id: string;
  company_id: string;
  field_key: keyof CompanyProfileData;
  value_json: { value: unknown };
  confidence: number;
  evidence_excerpt: string;
  source_locator_json: Record<string, unknown>;
  extraction_method: string;
  extraction_version: string;
  status: 'pending_review' | 'accepted' | 'rejected';
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface DocumentDetail {
  document: DocumentRecord;
  content: null | {
    parser: string;
    parser_version: string;
    text_sha256: string;
    character_count: number;
    page_count: number | null;
    language: string | null;
    metadata_json: Record<string, unknown>;
    preview: string;
  };
  chunk_count: number;
  candidates: DocumentFactCandidate[];
  ingestion_runs: Array<{
    id: string;
    document_id: string;
    attempt: number;
    status: string;
    parser_version: string;
    error_code: string | null;
    safe_message: string | null;
    metrics_json: Record<string, unknown>;
    started_at: string | null;
    finished_at: string | null;
    created_at: string;
  }>;
}

export interface PolicyScan {
  id: string;
  company_id: string;
  profile_version_id: string;
  task_id: string | null;
  workflow_run_id: string | null;
  status: string;
  total_opportunities: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
}

export type EligibilityStatus =
  | 'ELIGIBLE'
  | 'POTENTIALLY_ELIGIBLE'
  | 'NOT_ELIGIBLE'
  | 'NEED_MORE_INFORMATION';

export interface Opportunity {
  id: string;
  tenant_id: string;
  company_id: string;
  policy_id: string | null;
  policy_version_id: string | null;
  scan_id: string | null;
  profile_version_id: string | null;
  title: string;
  score: number | null;
  status: string;
  evidence_json: {
    score_breakdown?: Record<string, number>;
    missing_materials?: string[];
    gap_analysis_status?: string;
    [key: string]: unknown;
  };
  policy_snapshot_json: {
    title?: string;
    issuing_authority?: string | null;
    jurisdiction?: string | null;
    level?: string | null;
    province?: string | null;
    city?: string | null;
    district?: string | null;
    industry?: string | null;
    policy_type?: string | null;
    source_url?: string | null;
    published_at?: string | null;
    effective_at?: string | null;
    deadline?: string | null;
    support_amount?: string | null;
    support_type?: string | null;
  };
  eligibility_status: EligibilityStatus;
  eligibility_confidence: number | null;
  created_at: string;
  policy_content_available?: boolean;
  eligibility_result?: {
    id: string;
    policy_version_id: string | null;
    status: EligibilityStatus;
    confidence: number;
    summary: string;
    criteria: Array<{
      rule_id: string;
      name: string;
      fact_key: string;
      operator: string;
      expected: unknown;
      actual: unknown;
      is_hard_gate: boolean;
      status: 'PASS' | 'FAIL' | 'MISSING' | 'UNSUPPORTED' | 'UNVERIFIED_SOURCE';
      article: string | null;
    }>;
    missing_information: string[];
    engine_version: string;
    review_status: string;
    verified_at: string | null;
  } | null;
  evidence?: Array<{
    id: string;
    source_title: string;
    source_url: string | null;
    issuer: string | null;
    article: string | null;
    quote: string;
    confidence: number;
    verifier: string;
    verified: boolean;
  }>;
  required_materials?: Array<{
    id: string;
    name: string;
    description: string | null;
    is_hard_gate: boolean;
    article: string | null;
  }>;
  benefits?: Array<{
    id: string;
    benefit_type: string;
    description: string;
    amount_text: string | null;
    article: string | null;
  }>;
}

export interface ApplicationSummary {
  id: string;
  tenant_id: string;
  company_id: string;
  opportunity_id: string | null;
  title: string;
  status: string;
  form_data: Record<string, unknown>;
  owner_user_id: string | null;
  due_at: string | null;
  progress: number;
  review_status: string;
  created_at: string;
}

export interface ApplicationRequirement {
  id: string;
  title: string;
  description: string | null;
  category: string;
  status: string;
  is_hard_gate: boolean;
  source: Record<string, unknown>;
  sort_order: number;
}

export interface ApplicationActivity {
  id: string;
  action: string;
  summary: string;
  occurred_at: string;
}

export interface ApplicationDetail extends ApplicationSummary {
  company_name: string;
  opportunity: Opportunity | null;
  requirements: ApplicationRequirement[];
  activities: ApplicationActivity[];
  readiness: {
    requirement_total: number;
    requirement_ready: number;
    hard_gate_blockers: string[];
    missing_requirements: string[];
    linked_documents: number;
    verified_evidence: number;
    blockers: string[];
    can_submit_for_review: boolean;
  };
  evidence: Array<{
    id: string;
    source_title: string;
    source_url: string | null;
    issuer: string | null;
    article: string | null;
    quote: string;
    confidence: number;
    verified: boolean;
  }>;
  documents: Array<{
    link_id: string;
    document_id: string;
    requirement_id: string | null;
    filename: string;
    content_type: string;
    status: string;
    ingestion_status: string;
    created_at: string;
  }>;
  generated: ApplicationArtifact[];
  tasks: Array<{
    id: string;
    title: string;
    status: string;
    progress: number;
    current_stage: string | null;
  }>;
  comments: Array<{
    id: string;
    user_id: string | null;
    body: string;
    created_at: string;
  }>;
}

export interface ApplicationArtifact {
  id: string;
  artifact_type?: string;
  title: string;
  version: number;
  status: string;
  generation_method: string;
  checksum_sha256: string;
  source_snapshot: Record<string, unknown>;
  content: {
    executive_summary?: string;
    disclaimer?: string;
    [key: string]: unknown;
  };
  review_note: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface ApplicationAgentResponse {
  action: 'ask' | 'generate' | 'check' | 'fix' | 'explain';
  engine: string;
  message: string;
  readiness?: ApplicationDetail['readiness'];
  citations?: Array<{ source_title: string; article: string | null; quote: string; verified: boolean }>;
  artifact: ApplicationArtifact | null;
}

export interface Order {
  id: string;
  tenant_id: string;
  order_no?: string;
  product_code: string;
  amount: number;
  currency: string;
  resource_type?: string;
  resource_id?: string;
  status: string;
  created_at: string;
}

export interface BillingOverview {
  subscription: {
    id: string;
    status: string;
    provider: string;
    current_period_start: string;
    current_period_end: string;
    cancel_at_period_end: boolean;
    grace_ends_at: string | null;
  };
  plan: {
    code: string;
    name: string;
    sales_motion: string;
    limits: Record<string, number | null>;
    features: string[];
  };
  usage: Array<{ meter: string; used: number; limit: number | null; remaining: number | null }>;
  budgets: Array<{ id: string; scope_type: string; scope_id: string; meter_key: string; hard_limit: number; warning_threshold: number | null }>;
  orders: Order[];
  tax_invoices: Array<{ id: string; order_id: string; invoice_no: string | null; total_amount: number; status: string; created_at: string }>;
  paid_plan_checkout_available: boolean;
  paid_plan_checkout_message: string;
}

export interface PlanCatalogItem {
  code: string;
  name: string;
  description: string;
  tier: number;
  sales_motion: string;
  limits: Record<string, number | null>;
  features: string[];
  price: null | { version: number; currency: string; unit_amount: number; billing_interval: string; provider: string | null; checkout_available: boolean };
}

export interface EnterpriseSettings {
  apiKeys: Array<{ id: string; name: string; prefix: string; scopes: string[]; expires_at: string | null; last_used_at: string | null; revoked_at: string | null; created_at: string }>;
  retention: { document_days: number; agent_trace_days: number; analytics_days: number; audit_days: number; legal_hold: boolean; legal_hold_reason: string | null; enforcement_worker_available: boolean };
  exports: Array<{ id: string; status: string; format: string; scope: string; checksum_sha256: string | null; record_counts: Record<string, number>; created_at: string; completed_at: string | null }>;
  deletion: { request: null | { id: string; status: string; scheduled_for: string; reason: string | null; blockers: string[] }; execution_worker_available: boolean };
  flags: Record<string, boolean>;
}

export interface Report {
  id: string;
  company_id: string;
  content: string;
  model?: string;
  status: string;
  created_at: string;
}

export interface ProductCatalogItem {
  id: string;
  code: string;
  name: string;
  description: string;
  product_type: string;
  price: number;
  original_price: number | null;
  promotional_price: number | null;
  entitlement_type: string;
}

export interface Entitlement {
  id: string;
  product_code: string;
  product_name: string;
  resource_type: string;
  resource_id: string | null;
  status: string;
  created_at: string;
}

export interface TaskSummary {
  id: string;
  task_type?: string;
  title: string;
  status: string;
  progress?: number | null;
  current_stage?: string | null;
  created_at: string;
}

export interface TaskDeliverable {
  id: string;
  type: string;
  title: string;
  version: number;
  status: string;
  quality_score: number | null;
  pdf_url?: string | null;
  generated_at: string | null;
}

export interface TaskRunSummary {
  id: string;
  agent: string;
  status: string;
  prompt_version?: string | null;
  total_tokens: number;
  cost_usd: number;
  latency_ms?: number | null;
}

export interface AgentDefinitionSummary {
  id: string;
  key: string;
  name: string;
  description: string;
  version: string;
  status: string;
  run_count: number;
  completed_runs: number;
  failed_runs: number;
  success_rate: number | null;
  average_latency_ms: number | null;
  tasks_completed: number;
  last_run_at: string | null;
}

export interface AgentRunSummary {
  id: string;
  workflow_run_id: string | null;
  task_id: string | null;
  agent_key: string | null;
  agent_name: string;
  status: string;
  current_step: string | null;
  model: string;
  prompt_version: string | null;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number | null;
  retry_count: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_code: string | null;
}

export interface AgentStepTrace {
  id: string;
  sequence: number;
  agent_id: string | null;
  step_type: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  verification: Record<string, unknown>;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number | null;
  started_at: string | null;
  finished_at: string | null;
  error_code: string | null;
}

export interface AgentRunDetail extends AgentRunSummary {
  workflow_key: string | null;
  workflow_version: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  steps: AgentStepTrace[];
  tool_calls: Array<{
    id: string;
    agent_step_id: string;
    tool_name: string;
    status: string;
    arguments: Record<string, unknown>;
    result: Record<string, unknown>;
    latency_ms: number | null;
    started_at: string;
    finished_at: string | null;
    error_code: string | null;
  }>;
  errors: Array<{
    id: string;
    agent_step_id: string | null;
    code: string;
    category: string;
    safe_message: string;
    details: Record<string, unknown>;
    retryable: boolean;
    occurred_at: string;
  }>;
  retries: Array<{
    id: string;
    retry_number: number;
    reason_code: string;
    scheduled_at: string;
    started_at: string | null;
  }>;
  artifacts: Array<{
    id: string;
    task_id: string | null;
    application_id: string | null;
    artifact_type: string;
    title: string;
    version: number;
    status: string;
    mime_type: string | null;
    created_at: string;
  }>;
}

export interface TaskDetail extends TaskSummary {
  company_name: string;
  description?: string | null;
  payment_status?: string | null;
  deliverables: TaskDeliverable[];
  agent_runs: TaskRunSummary[];
}

export interface NextAction {
  action: string;
  desc: string;
  product_code: string | null;
  price: number;
  cta: string;
  href?: string | null;
}

export interface DemoScenarioSummary {
  key: string;
  title: string;
  industry: string;
  persona: string;
  summary: string;
  next_best_action: string;
  display_order: number;
}

export interface DemoScenarioList {
  dataset_version: string | null;
  data_classification: 'synthetic';
  data_notice: string;
  items: DemoScenarioSummary[];
}

export interface DemoScenarioDetail extends DemoScenarioSummary {
  dataset_version: string;
  data_classification: 'synthetic';
  data_notice: string;
  company: {
    id: string; name: string; industry: string; province: string; city: string;
    profile_version: number; completeness_score: number; profile: Record<string, unknown>;
  };
  document: {
    id: string; filename: string; content_type: string; ingestion_status: string;
    metadata: Record<string, unknown>;
  };
  scan: { id: string; status: string; provider: string; total_opportunities: number; completed_at: string };
  opportunity: {
    id: string; title: string; match_score: number; eligibility: string; confidence: number;
    potential_benefit: string; deadline: string; region: string; authority: string;
    policy_type: string; evidence_count: number;
  };
  eligibility: {
    id: string; status: string; confidence: number; summary: string;
    criteria: Array<Record<string, unknown>>; missing_information: string[];
    engine_version: string; review_status: string; verified_at: string;
  };
  evidence: Array<{
    id: string; conclusion: string; source_title: string; source_url: string; issuer: string;
    article: string; quote: string; publish_date: string; effective_date: string;
    expiry_date: string; region: string; confidence: number; verified: boolean; verifier: string;
  }>;
  application: {
    id: string; title: string; status: string; progress: number; review_status: string; due_at: string;
    requirements: Array<{ id: string; title: string; description: string; status: string; is_hard_gate: boolean }>;
    tasks: Array<{ id: string; title: string; status: string; priority: string; progress: number }>;
  };
  agent_run: {
    id: string; status: string; agent_name: string; model: string; latency_ms: number;
    tokens: number; cost_usd: number;
    steps: Array<{ sequence: number; type: string; status: string; output: Record<string, unknown>; verification: Record<string, unknown> }>;
    tool_calls: Array<{ tool_name: string; status: string; latency_ms: number; result: Record<string, unknown> }>;
  };
  artifact: {
    id: string; title: string; version: number; status: string; generation_method: string;
    checksum_sha256: string; content: Record<string, unknown>; formats: Array<'docx' | 'pdf' | 'xlsx' | 'json'>;
  };
}

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('yance_token');
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('yance_token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('yance_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    // Don't set Content-Type for FormData
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      throw new Error('认证已过期，请重新登录');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  private async requestBlob(path: string): Promise<Blob> {
    const headers: Record<string, string> = {};
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }
    const response = await fetch(`${API_BASE}${path}`, { headers });
    if (response.status === 401) {
      this.clearToken();
      throw new Error('认证已过期，请重新登录');
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '下载失败' }));
      throw new Error(error.detail || '下载失败');
    }
    return response.blob();
  }

  // Auth
  async login(email: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '登录失败' }));
      throw new Error(error.detail || '登录失败');
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async register(data: {
    company_name: string;
    industry?: string;
    province?: string;
    city?: string;
    owner_name: string;
    owner_email: string;
    owner_password: string;
  }): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '注册失败' }));
      throw new Error(error.detail || '注册失败');
    }
    const result = await response.json();
    if (result.access_token) this.setToken(result.access_token);
    return result;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async getAdminOverview(): Promise<AdminOverview> {
    return this.request<AdminOverview>('/admin/overview');
  }

  async getInvestorMetrics(): Promise<InvestorMetrics> {
    return this.request<InvestorMetrics>('/admin/investor-metrics');
  }

  async getEvaluationOverview(evalType?: EvalType): Promise<EvaluationOverview> {
    const query = evalType ? `?eval_type=${encodeURIComponent(evalType)}` : '';
    return this.request<EvaluationOverview>(`/admin/evals/overview${query}`);
  }

  async runEvaluations(evalType: EvalType | 'all' = 'all'): Promise<{
    batch_id: string;
    runs: EvalRunSummary[];
    release_gate_passed: boolean;
  }> {
    return this.request('/admin/evals/runs', {
      method: 'POST',
      body: JSON.stringify({ eval_type: evalType }),
    });
  }

  async getEvaluationRun(runId: string): Promise<EvalRunDetail> {
    return this.request<EvalRunDetail>(`/admin/evals/runs/${encodeURIComponent(runId)}`);
  }

  async getAdminResource(resource: string, offset: number = 0): Promise<AdminResourcePage> {
    return this.request<AdminResourcePage>(
      `/admin/resources/${encodeURIComponent(resource)}?limit=25&offset=${offset}`,
    );
  }

  async updateOrganizationStage(tenantId: string, accountStage: string): Promise<void> {
    await this.request(`/admin/organizations/${encodeURIComponent(tenantId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ account_stage: accountStage }),
    });
  }

  async updateFeedbackStatus(feedbackId: string, status: string): Promise<void> {
    await this.request(`/admin/feedback/${encodeURIComponent(feedbackId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  async recordOpportunityOpened(opportunityId: string): Promise<void> {
    await this.request(`/opportunities/${encodeURIComponent(opportunityId)}/opened`, {
      method: 'POST',
    });
  }

  // Tenant
  async getTenant(): Promise<Tenant> {
    return this.request<Tenant>('/tenant');
  }

  // Companies
  async getCompanies(): Promise<Company[]> {
    return this.request<Company[]>('/companies');
  }

  async getCompany(companyId: string): Promise<Company> {
    return this.request<Company>(`/companies/${encodeURIComponent(companyId)}`);
  }

  async createCompany(data: Partial<Company>): Promise<Company> {
    return this.request<Company>('/companies', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCompany(companyId: string, data: Partial<Company>): Promise<Company> {
    return this.request<Company>(`/companies/${encodeURIComponent(companyId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getCompanyProfile(companyId: string): Promise<CompanyProfile> {
    return this.request<CompanyProfile>(
      `/companies/${encodeURIComponent(companyId)}/profile`,
    );
  }

  async updateCompanyProfile(
    companyId: string,
    data: CompanyProfileData,
  ): Promise<CompanyProfile> {
    return this.request<CompanyProfile>(
      `/companies/${encodeURIComponent(companyId)}/profile`,
      { method: 'PUT', body: JSON.stringify(data) },
    );
  }

  async publishCompanyProfile(companyId: string): Promise<CompanyProfileVersion> {
    return this.request<CompanyProfileVersion>(
      `/companies/${encodeURIComponent(companyId)}/profile/publish`,
      { method: 'POST' },
    );
  }

  async getCompanyProfileVersions(companyId: string): Promise<CompanyProfileVersion[]> {
    return this.request<CompanyProfileVersion[]>(
      `/companies/${encodeURIComponent(companyId)}/profile/versions`,
    );
  }

  // Documents
  async getDocuments(): Promise<DocumentRecord[]> {
    return this.request<DocumentRecord[]>('/documents');
  }

  async presignDocumentUpload(data: {
    filename: string;
    content_type: string;
    company_id: string;
    size_bytes: number;
  }): Promise<{
    document: DocumentRecord;
    upload_url: string;
    method: string;
    expires_in: number;
    required_headers: Record<string, string>;
  }> {
    return this.request('/documents/presign-upload', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async completeDocumentUpload(documentId: string): Promise<DocumentRecord> {
    return this.request<DocumentRecord>(
      `/documents/${encodeURIComponent(documentId)}/complete`,
      { method: 'POST', body: JSON.stringify({}) },
    );
  }

  async getDocument(documentId: string): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/documents/${encodeURIComponent(documentId)}`);
  }

  async ingestDocument(documentId: string, force: boolean = false): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/documents/${encodeURIComponent(documentId)}/ingest`, {
      method: 'POST',
      body: JSON.stringify({ force }),
    });
  }

  async reviewDocumentFacts(
    documentId: string,
    decisions: Array<{
      candidate_id: string;
      decision: 'accept' | 'reject';
      value_json?: { value: unknown };
    }>,
  ): Promise<{ accepted: number; rejected: number; profile: CompanyProfile }> {
    return this.request(`/documents/${encodeURIComponent(documentId)}/facts/review`, {
      method: 'POST',
      body: JSON.stringify({ decisions }),
    });
  }

  async uploadDocument(companyId: string, file: File): Promise<DocumentRecord> {
    const presigned = await this.presignDocumentUpload({
      filename: file.name,
      content_type: file.type,
      company_id: companyId,
      size_bytes: file.size,
    });
    const upload = await fetch(presigned.upload_url, {
      method: presigned.method,
      headers: presigned.required_headers,
      body: file,
    });
    if (!upload.ok) throw new Error(`对象存储上传失败（HTTP ${upload.status}）`);
    const completed = await this.completeDocumentUpload(presigned.document.id);
    const detail = await this.ingestDocument(completed.id);
    return detail.document;
  }

  // Core workflow
  async getPolicyScans(companyId?: string): Promise<PolicyScan[]> {
    const query = companyId ? `?company_id=${encodeURIComponent(companyId)}` : '';
    return this.request<PolicyScan[]>(`/policy-scans${query}`);
  }

  async createPolicyScan(companyId: string, idempotencyKey: string): Promise<PolicyScan> {
    return this.request<PolicyScan>('/policy-scans', {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({ company_id: companyId }),
    });
  }

  async getOpportunities(filters?: {
    companyId?: string;
    scanId?: string;
  }): Promise<Opportunity[]> {
    const params = new URLSearchParams();
    if (filters?.companyId) params.set('company_id', filters.companyId);
    if (filters?.scanId) params.set('scan_id', filters.scanId);
    const query = params.size ? `?${params.toString()}` : '';
    return this.request<Opportunity[]>(`/opportunities${query}`);
  }

  async getOpportunity(opportunityId: string): Promise<Opportunity> {
    return this.request<Opportunity>(`/opportunities/${encodeURIComponent(opportunityId)}`);
  }

  async getApplications(): Promise<ApplicationSummary[]> {
    return this.request<ApplicationSummary[]>('/applications');
  }

  async createApplication(data: {
    company_id: string;
    opportunity_id: string;
    title: string;
  }): Promise<ApplicationSummary> {
    return this.request<ApplicationSummary>('/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getApplication(applicationId: string): Promise<ApplicationDetail> {
    return this.request<ApplicationDetail>(
      `/applications/${encodeURIComponent(applicationId)}`,
    );
  }

  async updateApplicationStatus(applicationId: string, status: string): Promise<ApplicationSummary> {
    return this.request<ApplicationSummary>(
      `/applications/${encodeURIComponent(applicationId)}/status`,
      { method: 'PATCH', body: JSON.stringify({ status }) },
    );
  }

  async updateRequirementStatus(
    applicationId: string,
    requirementId: string,
    status: string,
  ): Promise<void> {
    await this.request(
      `/applications/${encodeURIComponent(applicationId)}/requirements/${encodeURIComponent(requirementId)}`,
      { method: 'PATCH', body: JSON.stringify({ status }) },
    );
  }

  async linkApplicationDocument(applicationId: string, documentId: string, requirementId?: string): Promise<{ id: string; status: string }> {
    return this.request(`/applications/${encodeURIComponent(applicationId)}/documents`, {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId, requirement_id: requirementId || null }),
    });
  }

  async addApplicationComment(applicationId: string, body: string): Promise<void> {
    await this.request(`/applications/${encodeURIComponent(applicationId)}/comments`, {
      method: 'POST', body: JSON.stringify({ body }),
    });
  }

  async runApplicationAction(applicationId: string, action: ApplicationAgentResponse['action'], input?: { question?: string; instruction?: string }): Promise<ApplicationAgentResponse> {
    return this.request(`/applications/${encodeURIComponent(applicationId)}/agent-actions`, {
      method: 'POST', body: JSON.stringify({ action, ...input }),
    });
  }

  async reviewApplicationArtifact(applicationId: string, artifactId: string, decision: 'approve' | 'reject', note?: string): Promise<ApplicationArtifact> {
    return this.request(`/applications/${encodeURIComponent(applicationId)}/artifacts/${encodeURIComponent(artifactId)}/review`, {
      method: 'POST', body: JSON.stringify({ decision, note: note || null }),
    });
  }

  async editApplicationArtifact(applicationId: string, artifactId: string, executiveSummary: string): Promise<ApplicationArtifact> {
    return this.request(`/applications/${encodeURIComponent(applicationId)}/artifacts/${encodeURIComponent(artifactId)}/edit`, {
      method: 'POST', body: JSON.stringify({ executive_summary: executiveSummary }),
    });
  }

  async downloadApplicationArtifact(applicationId: string, artifactId: string, format: 'docx' | 'pdf' | 'xlsx' | 'json'): Promise<Blob> {
    return this.requestBlob(`/applications/${encodeURIComponent(applicationId)}/artifacts/${encodeURIComponent(artifactId)}/download?format=${format}`);
  }

  // Policies
  async searchPolicies(query: string, limit: number = 5): Promise<Policy[]> {
    const formData = new FormData();
    formData.append('query', query);
    formData.append('limit', limit.toString());

    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}/policies/search`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error('政策搜索失败');
    }

    return response.json();
  }

  // Reports
  async generateReport(companyId: string, query: string): Promise<Report> {
    const formData = new FormData();
    formData.append('company_id', companyId);
    formData.append('query', query);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '报告生成失败' }));
      throw new Error(error.detail || '报告生成失败');
    }

    return response.json();
  }

  // Orders
  async getOrders(): Promise<Order[]> {
    return this.request<Order[]>('/orders');
  }

  async getPlans(): Promise<PlanCatalogItem[]> {
    const result = await this.request<{ items: PlanCatalogItem[] }>('/billing/plans');
    return result.items;
  }

  async getBillingOverview(): Promise<BillingOverview> {
    return this.request<BillingOverview>('/billing/overview');
  }

  async getEnterpriseSettings(): Promise<EnterpriseSettings> {
    const [keys, retention, exports, deletion, flags] = await Promise.all([
      this.request<{ items: EnterpriseSettings['apiKeys'] }>('/enterprise/api-keys'),
      this.request<EnterpriseSettings['retention']>('/enterprise/retention'),
      this.request<{ items: EnterpriseSettings['exports'] }>('/enterprise/exports'),
      this.request<EnterpriseSettings['deletion']>('/enterprise/deletion-request'),
      this.request<{ flags: Record<string, boolean> }>('/enterprise/feature-flags'),
    ]);
    return { apiKeys: keys.items, retention, exports: exports.items, deletion, flags: flags.flags };
  }

  async createApiKey(name: string, scopes: string[]): Promise<{ secret: string }> {
    return this.request('/enterprise/api-keys', {
      method: 'POST',
      body: JSON.stringify({ name, scopes }),
    });
  }

  async revokeApiKey(keyId: string): Promise<void> {
    await this.request(`/enterprise/api-keys/${encodeURIComponent(keyId)}/revoke`, { method: 'POST' });
  }

  async createWorkspaceExport(): Promise<{ id: string }> {
    return this.request('/enterprise/exports', { method: 'POST' });
  }

  async downloadWorkspaceExport(jobId: string): Promise<Blob> {
    return this.requestBlob(`/enterprise/exports/${encodeURIComponent(jobId)}/download`);
  }

  async scheduleWorkspaceDeletion(reason?: string): Promise<{ id: string }> {
    return this.request('/enterprise/deletion-request', {
      method: 'POST',
      body: JSON.stringify({ reason: reason || null }),
    });
  }

  async cancelWorkspaceDeletion(requestId: string): Promise<void> {
    await this.request(`/enterprise/deletion-request/${encodeURIComponent(requestId)}/cancel`, { method: 'POST' });
  }

  async getProducts(): Promise<ProductCatalogItem[]> {
    return this.request<ProductCatalogItem[]>('/products');
  }

  async getEntitlements(): Promise<Entitlement[]> {
    return this.request<Entitlement[]>('/entitlements');
  }

  async createOrder(data: {
    product_code: string;
    resource_id: string;
  }): Promise<Order> {
    return this.request<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async createCheckout(orderId: string): Promise<{ url: string }> {
    return this.request<{ url: string }>(
      `/payments/checkout?order_id=${encodeURIComponent(orderId)}`,
      {
        method: 'POST',
      },
    );
  }

  // Demo: Match Report (with multi-model)
  async matchReport(companyId: string, provider: string = 'qwen'): Promise<{
    company_name: string;
    total_matches: number;
    preview: any[];
    full: any[];
    ai_summary: string;
    provider_used: string;
  }> {
    return this.request('/reports/match', {
      method: 'POST',
      body: JSON.stringify({ company_id: companyId, provider }),
    });
  }

  // Authorized report download
  async downloadReport(companyId: string): Promise<Blob> {
    return this.requestBlob(`/reports/${companyId}/download`);
  }

  // Tasks
  async getTasks(): Promise<TaskSummary[]> {
    return this.request<TaskSummary[]>('/tasks');
  }

  async getTask(taskId: string): Promise<TaskDetail> {
    return this.request<TaskDetail>(`/tasks/${encodeURIComponent(taskId)}`);
  }

  // Agent operations
  async getAgents(): Promise<AgentDefinitionSummary[]> {
    return this.request<AgentDefinitionSummary[]>('/agents');
  }

  async getAgentRuns(limit: number = 50): Promise<AgentRunSummary[]> {
    return this.request<AgentRunSummary[]>(`/agent-runs?limit=${limit}`);
  }

  async getAgentRun(runId: string): Promise<AgentRunDetail> {
    return this.request<AgentRunDetail>(`/agent-runs/${encodeURIComponent(runId)}`);
  }

  async getNextActions(taskId: string): Promise<NextAction[]> {
    const result = await this.request<{ actions: NextAction[] }>(
      `/tasks/${encodeURIComponent(taskId)}/next-actions`,
    );
    return result.actions;
  }

  async downloadTask(taskId: string): Promise<Blob> {
    return this.requestBlob(`/tasks/${encodeURIComponent(taskId)}/download`);
  }

  async acceptTask(taskId: string): Promise<void> {
    await this.request(`/tasks/${encodeURIComponent(taskId)}/accept`, { method: 'POST' });
  }

  async requestTaskRevision(taskId: string, deliverableId: string, request: string): Promise<void> {
    await this.request(`/tasks/${encodeURIComponent(taskId)}/revision`, {
      method: 'POST',
      body: JSON.stringify({ deliverable_id: deliverableId, request }),
    });
  }

  // Analytics: Stats (data flywheel)
  async getStats(): Promise<{
    period: string;
    total_events: number;
    searches: number;
    reports_generated: number;
    payments: number;
    downloads: number;
    provider_usage: Record<string, number>;
    available_models: Record<string, string>;
  }> {
    return this.request('/analytics/stats');
  }

  // Public investor demo. The API exposes only published synthetic tenants.
  async getDemoScenarios(): Promise<DemoScenarioList> {
    return this.request<DemoScenarioList>('/demo/scenarios');
  }

  async getDemoScenario(key: string): Promise<DemoScenarioDetail> {
    return this.request<DemoScenarioDetail>(`/demo/scenarios/${encodeURIComponent(key)}`);
  }

  async downloadDemoArtifact(
    key: string,
    artifactId: string,
    format: 'docx' | 'pdf' | 'xlsx' | 'json',
  ): Promise<Blob> {
    return this.requestBlob(
      `/demo/scenarios/${encodeURIComponent(key)}/artifacts/${encodeURIComponent(artifactId)}/download?format=${format}`,
    );
  }

  // Health
  async health(): Promise<{ status: string; version: string }> {
    const response = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
    return response.json();
  }
}

export const api = new ApiClient();
export default api;
