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
  tenant_id: string;
  title: string;
  source_url?: string;
  jurisdiction?: string;
  content: string;
  status: string;
  created_at: string;
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

    return response.json();
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

  async createCompany(data: Partial<Company>): Promise<Company> {
    return this.request<Company>('/companies', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCompany(companyId: string, data: Partial<Company>): Promise<Company> {
    return this.request<Company>(`/companies/${companyId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
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

  // Demo: Payment
  async demoPay(productCode: string = 'POLICY_REPORT', companyId?: string, opportunityId?: string): Promise<{
    order_id: string;
    order_no: string;
    payment_status: string;
    invoice_id: string;
    invoice_no: string;
    product_name: string;
    amount: number;
    message: string;
  }> {
    const body: any = { product_code: productCode };
    if (companyId) body.company_id = companyId;
    if (opportunityId) body.opportunity_id = opportunityId;
    return this.request('/payments/demo-pay', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // Demo: Download PDF
  async downloadReport(companyId: string): Promise<Blob> {
    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const response = await fetch(`${API_BASE}/reports/${companyId}/download`, { headers });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '下载失败' }));
      throw new Error(error.detail || '下载失败');
    }
    return response.blob();
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
