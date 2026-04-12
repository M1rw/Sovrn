const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

interface FetchOptions extends RequestInit {
  token?: string;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      data.detail || 'An error occurred',
      data
    );
  }

  return response.json();
}

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    fetchApi<{ access_token: string; refresh_token: string }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, name?: string) =>
    fetchApi<{ access_token: string; refresh_token: string }>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    }),

  refresh: (refreshToken: string) =>
    fetchApi<{ access_token: string; refresh_token: string }>('/api/v1/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  me: (token: string) =>
    fetchApi<User>('/api/v1/auth/me', { token }),
};

// Users
export const usersApi = {
  getProfile: (token: string) =>
    fetchApi<UserWithAccount>('/api/v1/users/me', { token }),

  updateProfile: (token: string, data: Partial<User>) =>
    fetchApi<User>('/api/v1/users/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
      token,
    }),
};

// Projects
export const projectsApi = {
  list: (token: string, params?: { page?: number; status?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return fetchApi<PaginatedResponse<Project>>(`/api/v1/projects?${query}`, { token });
  },

  get: (token: string, id: string) =>
    fetchApi<ProjectWithGenerations>(`/api/v1/projects/${id}`, { token }),

  create: (token: string, data: CreateProjectData) =>
    fetchApi<Project>('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify(data),
      token,
    }),

  update: (token: string, id: string, data: Partial<Project>) =>
    fetchApi<Project>(`/api/v1/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
      token,
    }),

  delete: (token: string, id: string) =>
    fetchApi<{ message: string }>(`/api/v1/projects/${id}`, {
      method: 'DELETE',
      token,
    }),

  generate: (token: string, id: string, data: GenerateSiteData) =>
    fetchApi<Job>(`/api/v1/projects/${id}/generate`, {
      method: 'POST',
      body: JSON.stringify(data),
      token,
    }),
};

// Jobs
export const jobsApi = {
  list: (token: string, params?: { page?: number; status?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return fetchApi<PaginatedResponse<Job>>(`/api/v1/jobs?${query}`, { token });
  },

  get: (token: string, id: string) =>
    fetchApi<Job>(`/api/v1/jobs/${id}`, { token }),

  cancel: (token: string, id: string) =>
    fetchApi<Job>(`/api/v1/jobs/${id}/cancel`, {
      method: 'POST',
      token,
    }),

  retry: (token: string, id: string) =>
    fetchApi<Job>(`/api/v1/jobs/${id}/retry`, {
      method: 'POST',
      token,
    }),
};

// Sparks
export const sparksApi = {
  getBalance: (token: string) =>
    fetchApi<Account>('/api/v1/sparks/balance', { token }),

  getHistory: (token: string, params?: { page?: number }) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return fetchApi<PaginatedResponse<SparkLedgerEntry>>(`/api/v1/sparks/history?${query}`, { token });
  },

  getPlans: () =>
    fetchApi<Plan[]>('/api/v1/sparks/plans'),

  createInvoice: (token: string, planType: string) =>
    fetchApi<Invoice>('/api/v1/sparks/invoices', {
      method: 'POST',
      body: JSON.stringify({ plan_type: planType }),
      token,
    }),
};

// Templates
export const templatesApi = {
  list: (params?: { page?: number; category?: string; industry?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return fetchApi<PaginatedResponse<Template>>(`/api/v1/templates?${query}`);
  },

  get: (id: string) =>
    fetchApi<Template>(`/api/v1/templates/${id}`),

  categories: () =>
    fetchApi<string[]>('/api/v1/templates/categories'),

  industries: () =>
    fetchApi<string[]>('/api/v1/templates/industries'),
};

// Types
export interface User {
  id: string;
  email: string;
  name?: string;
  locale: string;
  timezone: string;
  email_verified: boolean;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface Account {
  id: string;
  sparks_balance: number;
  sparks_used_total: number;
  plan: Plan;
  plan_started_at: string;
  plan_expires_at?: string;
}

export interface UserWithAccount extends User {
  account?: Account;
}

export interface Plan {
  id: string;
  name: string;
  type: string;
  sparks_included: number;
  price_cents: number;
  features: Record<string, unknown>;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  slug?: string;
  description?: string;
  status: string;
  locale: string;
  industry?: string;
  business_type?: string;
  brief?: string;
  created_at: string;
  updated_at: string;
  generated_at?: string;
  deployed_at?: string;
  deploy_url?: string;
}

export interface ProjectWithGenerations extends Project {
  generations: SiteGeneration[];
}

export interface SiteGeneration {
  id: string;
  project_id: string;
  job_id?: string;
  version: number;
  strategy_output: Record<string, unknown>;
  design_output: Record<string, unknown>;
  code_output: Record<string, unknown>;
  files: { path: string; language: string }[];
  lighthouse_scores: Record<string, unknown>;
  created_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  type: string;
  status: string;
  spark_cost: number;
  priority: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface SparkLedgerEntry {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  description?: string;
  reference_type?: string;
  created_at: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  amount_cents: number;
  currency: string;
  status: string;
  sparks_amount: number;
  payment_method?: string;
  payment_reference?: string;
  notes?: string;
  due_date?: string;
  paid_at?: string;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  slug: string;
  description?: string;
  category?: string;
  industry?: string;
  preview_url?: string;
  thumbnail_url?: string;
  is_premium: boolean;
  usage_count: number;
}

export interface CreateProjectData {
  name: string;
  description?: string;
  locale?: string;
  industry?: string;
  business_type?: string;
}

export interface GenerateSiteData {
  brief: string;
  locale?: string;
  industry?: string;
  business_type?: string;
  target_audience?: Record<string, unknown>;
  goals?: string[];
  template_id?: string;
  settings?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export { ApiError };
