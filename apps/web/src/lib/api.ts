import { createCorrelationId, getClientSessionId, recordRequestMetric } from '@/lib/telemetry';

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
  const method = (fetchOptions.method || 'GET').toUpperCase();
  const startedAt = Date.now();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  headers['X-Correlation-ID'] = createCorrelationId(endpoint);
  headers['X-Client-Session-ID'] = getClientSessionId();

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...fetchOptions,
      headers,
    });
  } catch (error) {
    recordRequestMetric(endpoint, method, 0, Date.now() - startedAt);
    throw error;
  }

  recordRequestMetric(endpoint, method, response.status, Date.now() - startedAt);

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

  previewArtifact: (
    token: string,
    id: string,
    params?: { generation_id?: string; entrypoint?: string }
  ) => {
    const query = new URLSearchParams();
    if (params?.generation_id) {
      query.set('generation_id', params.generation_id);
    }
    if (params?.entrypoint) {
      query.set('entrypoint', params.entrypoint);
    }

    const queryString = query.toString();
    const endpoint = queryString
      ? `/api/v1/projects/${id}/preview-artifact?${queryString}`
      : `/api/v1/projects/${id}/preview-artifact`;

    return fetchApi<PreviewArtifactResponse>(endpoint, { token });
  },

  previewArtifactFromEndpoint: (
    token: string,
    artifactEndpoint: string
  ) => fetchApi<PreviewArtifactResponse>(artifactEndpoint, { token }),

  createPreviewSession: (
    token: string,
    id: string,
    data: PreviewSessionRequestData = {}
  ) =>
    fetchApi<PreviewSessionResponse>(`/api/v1/projects/${id}/preview-session`, {
      method: 'POST',
      body: JSON.stringify(data),
      token,
    }),

  verifyPreviewSession: (
    id: string,
    data: PreviewSessionVerifyRequestData,
    token?: string
  ) =>
    fetchApi<PreviewSessionVerifyResponse>(`/api/v1/projects/${id}/preview-session/verify`, {
      method: 'POST',
      body: JSON.stringify(data),
      token,
    }),

  validatePatchContract: (
    token: string,
    id: string,
    data: PatchContractRequestData
  ) =>
    fetchApi<PatchContractValidationResponse>(`/api/v1/projects/${id}/patch-contract/validate`, {
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
  files: { path: string; content?: string; language?: string }[];
  lighthouse_scores: Record<string, unknown>;
  created_at: string;
}

export interface PreviewArtifactFile {
  path: string;
  content: string;
  language?: string;
  size_bytes: number;
}

export interface PreviewArtifactResponse {
  project_id: string;
  generation_id: string;
  generation_version: number;
  entrypoint: string;
  preview_html: string;
  files: PreviewArtifactFile[];
  source: string;
}

export interface PreviewSessionRequestData {
  generation_id?: string;
  entrypoint?: string;
  ttl_seconds?: number;
}

export interface PreviewSessionResponse {
  token: string;
  token_type: 'preview_session';
  expires_at: string;
  project_id: string;
  generation_id: string;
  entrypoint: string;
  artifact_endpoint: string;
}

export interface PreviewSessionVerifyRequestData {
  token: string;
  generation_id?: string;
  entrypoint?: string;
}

export interface PreviewSessionVerifyResponse {
  valid: true;
  token_type: 'preview_session';
  project_id: string;
  generation_id: string;
  entrypoint: string;
  expires_at: string;
  artifact_endpoint: string;
}

export type PatchContractVersion = '1.0';
export type PatchContractFallbackMode = 'safe_rewrite' | 'reject';
export type PatchContractLanguage = 'ts' | 'tsx' | 'js' | 'jsx' | 'json' | 'css' | 'html';
export type PatchContractOperationType = 'replace_file' | 'replace_range';

export interface PatchContractRange {
  start: number;
  end: number;
}

export interface PatchContractOperationData {
  op: PatchContractOperationType;
  path: string;
  language?: PatchContractLanguage;
  expected_sha256?: string;
  range?: PatchContractRange;
  content: string;
}

export interface PatchContractRequestData {
  version: PatchContractVersion;
  project_id?: string;
  generation_id?: string;
  fallback_mode?: PatchContractFallbackMode;
  operations: PatchContractOperationData[];
}

export interface PatchContractValidationResponse {
  valid: boolean;
  project_id: string;
  generation_id?: string;
  version: string;
  operation_count: number;
  files_touched: string[];
  fallback_mode: PatchContractFallbackMode;
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
  quality_mode?: 'fast' | 'balanced' | 'high';
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

export interface CanonicalGeneratedFile {
  name: string;
  content: string;
  type: string;
  size: number;
}

export interface CanonicalJobResolution {
  ok: boolean;
  previewHtml?: string;
  files?: CanonicalGeneratedFile[];
  generationId?: string;
  generationTimeMs?: number;
  source?: 'generation-record' | 'job-output';
  error?: string;
}

export interface PreviewStreamQuery {
  generation_id?: string;
  entrypoint?: string;
  preview_token?: string;
  poll_interval_ms?: number;
}

export function buildPreviewEventsStreamPath(projectId: string, query: PreviewStreamQuery): string {
  const params = new URLSearchParams();
  if (query.generation_id) {
    params.set('generation_id', query.generation_id);
  }
  if (query.entrypoint) {
    params.set('entrypoint', query.entrypoint);
  }
  if (query.preview_token) {
    params.set('preview_token', query.preview_token);
  }
  if (typeof query.poll_interval_ms === 'number' && Number.isFinite(query.poll_interval_ms)) {
    params.set('poll_interval_ms', String(Math.trunc(query.poll_interval_ms)));
  }

  const suffix = params.toString();
  return suffix
    ? `/api/v1/projects/${projectId}/preview-events?${suffix}`
    : `/api/v1/projects/${projectId}/preview-events`;
}

function normalizeFile(name: string, content: string): CanonicalGeneratedFile {
  const type = name.includes('.') ? name.split('.').pop() || 'txt' : 'txt';
  return {
    name,
    content,
    type,
    size: new TextEncoder().encode(content).length,
  };
}

function filesFromMap(raw: unknown): CanonicalGeneratedFile[] {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return [];
  }

  return Object.entries(raw as Record<string, unknown>).map(([name, content]) => {
    const textContent = typeof content === 'string' ? content : JSON.stringify(content ?? '');
    return normalizeFile(name, textContent);
  });
}

function filesFromGeneration(raw: unknown): CanonicalGeneratedFile[] {
  if (!Array.isArray(raw)) {
    return [];
  }

  const parsed: CanonicalGeneratedFile[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') {
      continue;
    }

    const path = (item as { path?: unknown }).path;
    const content = (item as { content?: unknown }).content;
    if (typeof path !== 'string') {
      continue;
    }

    parsed.push(normalizeFile(path, typeof content === 'string' ? content : ''));
  }

  return parsed;
}

export function resolveCanonicalJobResult(job: Job, project: ProjectWithGenerations): CanonicalJobResolution {
  if (job.status === 'failed') {
    return {
      ok: false,
      error: job.error || 'Generation failed during canonical job processing.',
    };
  }

  if (job.status !== 'completed') {
    return {
      ok: false,
      error: `Generation job is not complete (status: ${job.status}).`,
    };
  }

  const generations = Array.isArray(project.generations) ? project.generations : [];
  const matching = generations.filter((generation) => generation.job_id === job.id);
  const candidates = matching.length > 0 ? matching : generations;

  if (candidates.length > 0) {
    const sorted = [...candidates].sort((a, b) => {
      const versionDelta = (b.version || 0) - (a.version || 0);
      if (versionDelta !== 0) {
        return versionDelta;
      }
      return Date.parse(b.created_at || '') - Date.parse(a.created_at || '');
    });
    const chosen = sorted[0];
    const files = filesFromGeneration(chosen.files);
    const codeOutput = chosen.code_output || {};
    const previewHtml = typeof codeOutput.preview_html === 'string'
      ? codeOutput.preview_html
      : files.find((file) => file.name === 'index.html')?.content || '';

    if (previewHtml) {
      return {
        ok: true,
        previewHtml,
        files,
        generationId: chosen.id,
        generationTimeMs: typeof codeOutput.generation_time_ms === 'number' ? codeOutput.generation_time_ms : undefined,
        source: 'generation-record',
      };
    }
  }

  const output = (job.output || {}) as Record<string, unknown>;
  const files = filesFromMap(output.files);
  const previewHtml = typeof output.preview_html === 'string'
    ? output.preview_html
    : files.find((file) => file.name === 'index.html')?.content || '';

  if (previewHtml) {
    return {
      ok: true,
      previewHtml,
      files,
      generationId: typeof output.generation_id === 'string' ? output.generation_id : undefined,
      generationTimeMs: typeof output.generation_time_ms === 'number' ? output.generation_time_ms : undefined,
      source: 'job-output',
    };
  }

  return {
    ok: false,
    error: 'Canonical job completed but no persisted artifacts could be resolved.',
  };
}

export { ApiError };
