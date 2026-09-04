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
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  role: string;
  is_active: boolean;
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
  source_type: string;
  ingestion_status: string;
  ingestion_error: string | null;
  ingested_at: string | null;
  created_at: string;
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
    return this.completeDocumentUpload(presigned.document.id);
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

  // Health
  async health(): Promise<{ status: string; version: string }> {
    const response = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
    return response.json();
  }
}

export const api = new ApiClient();
export default api;
